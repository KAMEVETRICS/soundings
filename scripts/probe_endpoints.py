import json
import sys
import time
import urllib.request

base = "http://127.0.0.1:8001"


def hit(path: str, timeout: int = 90) -> None:
    t0 = time.time()
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            dt = time.time() - t0
            extra = ""
            if body[:1] in "{[":
                data = json.loads(body)
                extra = f" ok={data.get('ok')}"
                if data.get("error"):
                    extra += f" err={str(data.get('error'))[:80]}"
                stress = data.get("stress") or {}
                if stress.get("S") is not None:
                    extra += f" S={stress.get('S'):.3f} gap={(stress.get('gap') or {}).get('code')}"
                if data.get("endpoints"):
                    extra += f" n={len(data['endpoints'])}"
                if data.get("rows"):
                    extra += f" rows={len(data['rows'])}"
                if data.get("funding"):
                    extra += f" crowding={(data.get('funding') or {}).get('crowding')}"
                if data.get("value") is not None:
                    extra += f" fg={data.get('value')}"
            else:
                extra = f" html={len(body)}"
                if "Positioning stress" in body:
                    extra += " has_s"
                if "Crowd vs tape" in body or "what the crowd feels" in body.lower():
                    extra += " has_hero"
                if "Traceback" in body or "Internal Server Error" in body:
                    extra += " ERROR"
            print(f"{response.status} {path} {dt:.1f}s{extra}", flush=True)
    except Exception as exc:
        print(f"FAIL {path} {type(exc).__name__}: {exc}", flush=True)


def main() -> None:
    for path in [
        "/api/health",
        "/api",
        "/api/overview",
        "/api/screener",
        "/api/analytics",
        "/api/compare?symbols=SOL,ETH,BTC",
        "/api/catalog",
        "/",
        "/analytics",
        "/screener",
        "/sentiment",
        "/insights",
        "/compare?symbols=SOL,ETH,BTC",
        "/claw",
        "/api/token/SOL",
        "/token/SOL",
    ]:
        hit(path)


if __name__ == "__main__":
    main()
    sys.exit(0)
