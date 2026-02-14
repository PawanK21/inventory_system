import uuid
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Item, InventoryLot, InventoryLedger
from .forms import RegisterForm, LoginForm
from .services import reserve_inventory, issue_inventory, get_stock_summary


def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.save()
        return redirect("login")
    return render(request, "inventory/register.html", {"form": form})


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user:
            login(request, user)
            return redirect("dashboard")
    return render(request, "inventory/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    items = Item.objects.all()
    return render(request, "inventory/dashboard.html", {"items": items})


@login_required
def stock_summary(request, item_id):
    item = Item.objects.get(id=item_id)
    return JsonResponse(get_stock_summary(item))


@login_required
def receive_inventory(request):
    if request.method == "POST":
        item = Item.objects.get(id=request.POST["itemId"])
        qty = int(request.POST["qty"])

        lot = InventoryLot.objects.create(
            item=item,
            lotCode=str(uuid.uuid4())[:8],
            receivedQty=qty,
            qcStatus="QUARANTINE" if item.qcRequired else "APPROVED",
        )

        InventoryLedger.objects.create(
            item=item,
            lot=lot,
            txnType="RECEIVE",
            qty=qty,
            idempotencyKey=str(uuid.uuid4()),
        )

        return JsonResponse({"status": "RECEIVED"})


from django.db import transaction
from django.db.models import Sum
from .models import InventoryLedger, InventoryLot


def get_stock_summary(item):
    received = InventoryLedger.objects.filter(
        item=item, txnType="RECEIVE"
    ).aggregate(Sum("qty"))["qty__sum"] or 0

    issued = InventoryLedger.objects.filter(
        item=item, txnType="ISSUE"
    ).aggregate(Sum("qty"))["qty__sum"] or 0

    reserved = (
        InventoryLedger.objects.filter(item=item, txnType="RESERVE")
        .aggregate(Sum("qty"))["qty__sum"] or 0
    ) - (
        InventoryLedger.objects.filter(item=item, txnType="UNRESERVE")
        .aggregate(Sum("qty"))["qty__sum"] or 0
    )

    onHand = received - issued
    available = onHand - reserved

    return {
        "onHand": onHand,
        "reserved": reserved,
        "available": available,
    }


@transaction.atomic
def reserve_inventory(item, qty, idempotencyKey):
    if InventoryLedger.objects.filter(idempotencyKey=idempotencyKey).exists():
        return "IDEMPOTENT_REPLAY"

    summary = get_stock_summary(item)
    if summary["available"] < qty:
        raise Exception("INSUFFICIENT_STOCK")

    lot = InventoryLot.objects.filter(
        item=item, qcStatus="APPROVED"
    ).first()

    if not lot:
        raise Exception("NO_QC_APPROVED_LOT")

    InventoryLedger.objects.create(
        item=item,
        lot=lot,
        txnType="RESERVE",
        qty=qty,
        idempotencyKey=idempotencyKey,
    )


@transaction.atomic
def issue_inventory(item, qty, idempotencyKey):
    if InventoryLedger.objects.filter(idempotencyKey=idempotencyKey).exists():
        return "IDEMPOTENT_REPLAY"

    summary = get_stock_summary(item)
    if summary["reserved"] < qty:
        raise Exception("RESERVATION_NOT_FOUND")

    lot = InventoryLot.objects.filter(
        item=item, qcStatus="APPROVED"
    ).first()

    if not lot:
        raise Exception("NO_QC_APPROVED_LOT")

    InventoryLedger.objects.create(
        item=item,
        lot=lot,
        txnType="ISSUE",
        qty=qty,
        idempotencyKey=idempotencyKey,
    )

    InventoryLedger.objects.create(
        item=item,
        lot=lot,
        txnType="UNRESERVE",
        qty=qty,
        idempotencyKey=idempotencyKey + "_UNRESERVE",
    )
