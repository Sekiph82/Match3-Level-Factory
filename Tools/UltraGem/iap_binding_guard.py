"""Non-minting IAP binding validation for unverified Apple/Google metadata.

LFX-M13-004. A matching store SKU is not proof of paid purchase. Entitlement
issuance requires authoritative server receipt verification and Engine/liveops
policy. This module only checks authoring consistency.
"""
from __future__ import annotations

from typing import Any


def audit_iap_entitlement_bindings(store_catalog: dict[str,Any],
                                   bindings: list[dict[str,Any]]) -> dict[str,Any]:
    if not isinstance(store_catalog,dict) or (
        store_catalog.get("resultStatus")!="STORE_CATALOG_AUTHORING_ONLY"
        or store_catalog.get("engineStatus")!="BLOCKED_ENG_M24"
        or store_catalog.get("entitlementOrPurchaseAuthorized") is not False):
        raise ValueError("valid non-authoritative SKU catalog required")
    products=store_catalog.get("products")
    if not isinstance(products,list) or not isinstance(bindings,list) or len(bindings)>128:
        raise ValueError("bindings must be a bounded list")
    catalog={}
    for product in products:
        if not isinstance(product,dict) or product.get("clientCanMintEntitlement") is not False or product.get("serverReceiptVerificationRequired") is not True:
            raise ValueError("SKU catalog contains an unverified entitlement grant path")
        key=(product["profileId"],product["store"],product["skuId"])
        if key in catalog:
            raise ValueError("duplicate SKU catalog keys")
        catalog[key]=product
    seen=set()
    items=[]
    for record in bindings:
        if not isinstance(record,dict) or set(record)!={"profileId","store","skuId","entitlementId"}:
            raise ValueError("unknown or missing authoring binding fields")
        key=(record["profileId"],record["store"],record["skuId"])
        if key in seen or key not in catalog:
            raise ValueError("unlisted/duplicate SKU binding")
        seen.add(key)
        product=catalog[key]
        if record["entitlementId"]!=product["entitlementId"]:
            raise ValueError("entitlement mismatch")
        items.append({
            **record,
            "productType":product["productType"],
            "catalogExistenceVerified":False,
            "storeReceiptValidated":False,
            "clientEntitlementMintAllowed":False,
            "childLegalReviewNeeded":record["profileId"]=="Wonder_Pop",
        })
    return {
        "resultStatus":"IAP_BINDING_AUDIT_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "bindings":sorted(items,key=lambda x:(x["profileId"],x["store"],x["skuId"])),
        "runtimeStorePricesAvailable":False,
        "storeVerificationPerformed":False,
        "entitlementsIssued":0,
        "publisherAuthorized":False,
    }
