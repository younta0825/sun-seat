"""경기도 버스 API(GBIS)에서 65번, 5006번 노선의 정류장과 경로 좌표를 받아 data/ 폴더에 저장합니다.
실행: python3 fetch_routes.py
"""
import json, os, sys, urllib.parse, urllib.request

BASE = "https://apis.data.go.kr/6410000/busrouteservice/v2"
ROUTES = ["65", "5006"]
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load_key():
    path = os.path.join(HERE, ".env")
    if not os.path.exists(path):
        sys.exit(".env 파일이 없어요. .env.example을 복사해서 .env로 만들고 GBIS_KEY= 뒤에 인증키를 넣어주세요.")
    for line in open(path, encoding="utf-8"):
        if line.strip().startswith("GBIS_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    sys.exit(".env에 GBIS_KEY 값이 비어 있어요.")


def call(op, key, **params):
    # Encoding 키(%가 들어있음)는 그대로, Decoding 키는 URL 인코딩해서 사용
    k = key if "%" in key else urllib.parse.quote(key, safe="")
    qs = "&".join(f"{a}={urllib.parse.quote(str(b))}" for a, b in params.items())
    url = f"{BASE}/{op}?serviceKey={k}&format=json&{qs}"
    with urllib.request.urlopen(url, timeout=20) as r:
        raw = r.read().decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(f"[{op}] JSON이 아닌 응답이 왔어요 (키 등록이 아직 안 됐을 수 있어요):\n{raw[:500]}")
    resp = data.get("response", data)
    header = resp.get("msgHeader", {})
    if str(header.get("resultCode", "0")) not in ("0", "00"):
        print(f"  [{op}] 결과: {header.get('resultCode')} {header.get('resultMessage')}")
    body = resp.get("msgBody") or {}
    return body, data


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def main():
    key = load_key()
    os.makedirs(DATA, exist_ok=True)
    summary = []
    for num in ROUTES:
        body, raw = call("getBusRouteListv2", key, keyword=num)
        found = [r for r in as_list(body.get("busRouteList")) if str(r.get("routeName")) == num]
        if not found:
            print(f"{num}번: 노선을 못 찾았어요. 응답 일부:\n{json.dumps(raw, ensure_ascii=False)[:600]}")
            continue
        for r in found:
            rid = r.get("routeId")
            print(f"{num}번 [{r.get('regionName')}] {r.get('startStationName')} → {r.get('endStationName')} (routeId {rid})")
            st, _ = call("getBusRouteStationListv2", key, routeId=rid)
            ln, _ = call("getBusRouteLineListv2", key, routeId=rid)
            out = {
                "route": r,
                "stations": as_list(st.get("busRouteStationList")),
                "line": as_list(ln.get("busRouteLineList")),
            }
            fn = os.path.join(DATA, f"route_{num}_{rid}.json")
            json.dump(out, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"   정류장 {len(out['stations'])}개, 경로 좌표 {len(out['line'])}개 저장 → {os.path.relpath(fn, HERE)}")
            summary.append(os.path.basename(fn))
    print("\n완료!" if summary else "\n저장된 노선이 없어요. 위 메시지를 Claude에게 보여주세요.")


if __name__ == "__main__":
    main()
