// 햇빛 좌석 계산 로직 (브라우저와 node 둘 다에서 동작)
(function (root) {
  const RAD = Math.PI / 180;

  // 태양 위치: 고도(alt, 도)와 방위각(az, 북=0 시계방향, 도)
  function sunPosition(date, lat, lon) {
    const n = date.getTime() / 86400000 + 2440587.5 - 2451545.0;
    const L = (280.46 + 0.9856474 * n) % 360;
    const g = ((357.528 + 0.9856003 * n) % 360) * RAD;
    const lam = (L + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * RAD;
    const eps = (23.439 - 0.0000004 * n) * RAD;
    const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam));
    const dec = Math.asin(Math.sin(eps) * Math.sin(lam));
    const gmst = (18.697374558 + 24.06570982441908 * n) % 24;
    const H = (gmst * 15 + lon) * RAD - ra;
    const la = lat * RAD;
    const alt = Math.asin(Math.sin(la) * Math.sin(dec) + Math.cos(la) * Math.cos(dec) * Math.cos(H));
    const az = Math.atan2(-Math.sin(H), Math.tan(dec) * Math.cos(la) - Math.sin(la) * Math.cos(H));
    return { alt: alt / RAD, az: ((az / RAD) + 360) % 360 };
  }

  function bearing(a, b) { // a,b = [lon, lat]
    const p1 = a[1] * RAD, p2 = b[1] * RAD, dl = (b[0] - a[0]) * RAD;
    const y = Math.sin(dl) * Math.cos(p2);
    const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return ((Math.atan2(y, x) / RAD) + 360) % 360;
  }

  function meters(a, b) {
    const dx = (b[0] - a[0]) * 111320 * Math.cos(((a[1] + b[1]) / 2) * RAD);
    const dy = (b[1] - a[1]) * 110540;
    return Math.hypot(dx, dy);
  }

  // 구간 속도 가정 (km/h): 고속도로 경유 구간은 빠르게, 시내는 느리게
  function segmentSpeed(route, s1, s2) {
    if (s1.via || s2.via) return 65;
    return route.type.includes("직행") ? 20 : 16;
  }

  // 탈 정류장 i ~ 내릴 정류장 j 사이 경로를 시간 정보와 함께 펼침
  function buildTrip(route, i, j) {
    const st = route.stations, line = route.line;
    const segs = []; // {a,b,len,sec}
    let total = 0;
    for (let k = i; k < j; k++) {
      const s1 = st[k], s2 = st[k + 1];
      const v = segmentSpeed(route, s1, s2) / 3.6;
      for (let p = s1.li; p < s2.li; p++) {
        const a = line[p], b = line[p + 1], len = meters(a, b);
        if (len < 0.5) continue;
        segs.push({ a, b, len, sec: len / v });
        total += len / v;
      }
    }
    return { segs, estSec: total };
  }

  // 핵심 계산: 일정 간격으로 샘플링하면서 해가 버스 기준 어느 쪽에 있는지 누적
  function analyze(route, i, j, departDate, tripMinutes) {
    const { segs, estSec } = buildTrip(route, i, j);
    const scale = tripMinutes ? (tripMinutes * 60) / estSec : 1;
    const tripSec = estSec * scale;
    const acc = { L: 0, R: 0, F: 0, B: 0, sunSec: 0, darkSec: 0, sunL: 0, sunR: 0 };
    const samples = []; // 타임라인/지도용
    let t = 0;
    for (const s of segs) {
      const dt = s.sec * scale;
      const mid = [(s.a[0] + s.b[0]) / 2, (s.a[1] + s.b[1]) / 2];
      const when = new Date(departDate.getTime() + (t + dt / 2) * 1000);
      const sun = sunPosition(when, mid[1], mid[0]);
      const head = bearing(s.a, s.b);
      let side = 0, rel = 0, strength = 0;
      if (sun.alt > 0) {
        rel = (((sun.az - head) % 360) + 540) % 360 - 180; // -180~180, +면 오른쪽
        const sn = Math.sin(rel * RAD), cs = Math.cos(rel * RAD);
        // 해가 낮을수록 옆 창으로 깊게 들어옴. 너무 높으면(70도 이상) 옆 창 영향 작음
        const k = Math.cos(sun.alt * RAD) * Math.min(1, sun.alt / 4 + 0.25);
        acc.R += Math.max(0, sn) * k * dt;
        acc.L += Math.max(0, -sn) * k * dt;
        acc.F += Math.max(0, cs) * k * dt;
        acc.B += Math.max(0, -cs) * k * dt;
        acc.sunSec += dt;
        if (sn > 0.2) acc.sunR += dt; else if (sn < -0.2) acc.sunL += dt;
        side = sn > 0.2 ? 1 : sn < -0.2 ? -1 : 0;
        strength = Math.abs(sn) * k;
      } else acc.darkSec += dt;
      samples.push({ t, dt, a: s.a, b: s.b, side, strength, alt: sun.alt, az: sun.az, head });
      t += dt;
    }
    const T = Math.max(tripSec, 1);
    // 좌석 구역별 노출 지수(0~1): 옆 창 + 앞유리/뒷유리 영향
    const zones = {
      leftFront: (acc.L + 0.6 * acc.F) / T, leftMid: (acc.L + 0.15 * acc.F) / T, leftBack: (acc.L + 0.3 * acc.B) / T,
      rightFront: (acc.R + 0.6 * acc.F) / T, rightMid: (acc.R + 0.15 * acc.F) / T, rightBack: (acc.R + 0.3 * acc.B) / T,
    };
    return { tripSec, estSec, acc, zones, samples };
  }

  const api = { sunPosition, bearing, meters, buildTrip, analyze };
  if (typeof module !== "undefined") module.exports = api; else root.SunSeat = api;
})(this);
