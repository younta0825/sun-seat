"""data/의 원본 JSON을 웹 화면용 web/routes.js로 가공합니다.
각 정류장을 경로 좌표(line) 위의 가장 가까운 점에 순서대로 매칭해 둡니다.
실행: python3 build_data.py
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = [  # (파일, 화면에 보일 이름)
    ("route_5006_228000262.json", "5006 광교차고지 ↔ 강남"),
    ("route_65_234000038.json", "65 광교차고지 ↔ 안양역"),
]


def dist2(a, b):
    dx = (a[0] - b[0]) * math.cos(math.radians(a[1]))
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def build(fn, label):
    d = json.load(open(os.path.join(HERE, "data", fn), encoding="utf-8"))
    line = [(float(p["x"]), float(p["y"])) for p in sorted(d["line"], key=lambda p: int(p["lineSeq"]))]
    stations = sorted(d["stations"], key=lambda s: int(s["stationSeq"]))
    out_st, idx = [], 0
    for s in stations:
        pt = (float(s["x"]), float(s["y"]))
        # 앞으로만 탐색해서 왕복 노선에서 반대 방향 점에 붙지 않게 함
        window = range(idx, min(len(line), idx + 400))
        best = min(window, key=lambda i: dist2(line[i], pt))
        idx = best
        out_st.append({
            "name": s["stationName"].strip(),
            "seq": int(s["stationSeq"]),
            "li": best,
            "via": "(경유)" in s["stationName"],
            "turn": s.get("turnYn") == "Y",
        })
    r = d["route"]
    return {
        "id": str(r["routeId"]),
        "label": label,
        "type": r.get("routeTypeName", ""),
        "line": [[round(x, 6), round(y, 6)] for x, y in line],
        "stations": out_st,
    }


routes = [build(fn, label) for fn, label in TARGETS]
with open(os.path.join(HERE, "web", "routes.js"), "w", encoding="utf-8") as f:
    f.write("// build_data.py가 만든 파일입니다. 직접 수정하지 마세요.\n")
    f.write("window.ROUTES = " + json.dumps(routes, ensure_ascii=False, separators=(",", ":")) + ";\n")
for r in routes:
    lis = [s["li"] for s in r["stations"]]
    print(r["label"], "정류장", len(r["stations"]), "경로점", len(r["line"]), "단조증가:", lis == sorted(lis))

# 한 파일짜리 배포본 만들기 (web/sun-seat-standalone.html, docs/index.html)
page = open(os.path.join(HERE, "web", "index.html"), encoding="utf-8").read()
for name in ("routes.js", "sun.js"):
    js = open(os.path.join(HERE, "web", name), encoding="utf-8").read()
    page = page.replace(f'<script src="{name}"></script>', "<script>" + js + "</script>")
os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
for out in (os.path.join(HERE, "web", "sun-seat-standalone.html"), os.path.join(HERE, "docs", "index.html")):
    open(out, "w", encoding="utf-8").write(page)
print("배포본 생성: docs/index.html")
