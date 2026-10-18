"""Offline SKU catalog authoring, not store/entitlement authority.

LFX-M13-001. Product IDs are unverified draft references, and real prices /
currency / eligibility MUST be loaded from signed Apple/Google storefront APIs.
No receipt verification, purchase, grant or client-set price is possible here.
"""
from __future__ import annotations

import re
from typing import Any

from theme_contract import PROFILES

STORES=("APPLE_APP_STORE","GOOGLE_PLAY")
KINDS=("CONSUMABLE","NON_CONSUMABLE","SUBSCRIPTION")
REQUIRED_FIELDS=frozenset(("profileId","store","appNamespace","skuId",
                          "productType","descriptionKey","entitlementId"))
MAX_PRODUCTS=128


def propose_store_catalog(items: list[dict[str,Any]]) -> dict[str,Any]:
    if not isinstance(items,list) or len(items)>MAX_PRODUCTS:
        raise ValueError("store catalog must be a bounded list")
    seen=set()
    catalog=[]
    for record in items:
        if not isinstance(record,dict) or set(record)!=REQUIRED_FIELDS:
            raise ValueError("unknown, missing, or price-related store fields")
        profile,store,namespace,sku,kind,description,entitlement=(
            record[k] for k in ("profileId","store","appNamespace","skuId",
                                "productType","descriptionKey","entitlementId"))
        if profile not in PROFILES or store not in STORES or kind not in KINDS:
            raise ValueError("invalid game/store/product type")
        if not isinstance(namespace,str) or re.fullmatch(r"[a-z][a-z0-9_.]{4,99}",namespace) is None:
            raise ValueError("app namespace must be a bounded identifier")
        if not isinstance(sku,str) or re.fullmatch(r"[a-z][a-z0-9._-]{6,127}",sku) is None or not sku.startswith(namespace+"."):
            raise ValueError("SKU must belong to stated app namespace")
        if not isinstance(description,str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{2,127}",description) is None:
            raise ValueError("description must be a localization key")
        if not isinstance(entitlement,str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{2,127}",entitlement) is None:
            raise ValueError("entitlement must be a symbolic ID only")
        key=(store,namespace,sku)
        if key in seen:
            raise ValueError("duplicate store SKU")
        seen.add(key)
        catalog.append({
            **record,
            "storeSkuExistenceVerified":False,
            "storePriceOrCurrencyCached":False,
            "serverReceiptVerificationRequired":True,
            "clientCanMintEntitlement":False,
            "ownerAndStoreApprovalPending":True,
            "childPolicyRequiresIndependentReview":profile=="Wonder_Pop",
        })
    return {
        "schemaVersion":1,
        "resultStatus":"STORE_CATALOG_AUTHORING_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "products":sorted(catalog,key=lambda d:(d["profileId"],d["store"],d["skuId"])),
        "liveStorePricingSource":"STORE_RUNTIME_ONLY",
        "containsStaticPriceOrCurrency":False,
        "entitlementOrPurchaseAuthorized":False,
        "releaseAuthorized":False,
    }
