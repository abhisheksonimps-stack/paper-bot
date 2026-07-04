import requests, time, json, os
from datetime import datetime, timezone

WATCHLIST   = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT"]
INTERVAL    = "1h"; LOOKBACK=3; FETCH_LIMIT=500
FEE_PCT=0.05; SLIPPAGE_PCT=0.02; RISK_PER_TRADE=1.0; START_EQUITY=10000.0
ER_WINDOW=30; MAX_HOLD_CANDLES=200

STRATS = {
    "ORIGINAL": dict(DOUBLE_CONFIRM=True, USE_ER=False, ER_MIN=0.0,
                     MIN_RR=0.0, TARGET_LIQ_IDX=0, ledger="ledger_original.json"),
    "MODIFIED": dict(DOUBLE_CONFIRM=True, USE_ER=True,  ER_MIN=0.30,
                     MIN_RR=2.0, RR_TARGET=2.5, ledger="ledger_modified.json"),
}

def fetch(sym, iv, limit):
    url=f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={iv}&limit={limit}"
    r=requests.get(url,timeout=30); r.raise_for_status()
    rows=r.json()[:-1]   # drop still-forming candle
    return [{"t":x[0],"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4])} for x in rows]
def eff_ratio(cl,i,n):
    if i<n: return None
    net=abs(cl[i]-cl[i-n]); path=sum(abs(cl[j]-cl[j-1]) for j in range(i-n+1,i+1))
    return net/path if path>0 else 0
def detect_swings(c,lb=3):
    H,L=[],[]
    for i in range(lb,len(c)-lb):
        ih=il=True
        for j in range(i-lb,i+lb+1):
            if j==i: continue
            if c[j]["h"]>=c[i]["h"]: ih=False
            if c[j]["l"]<=c[i]["l"]: il=False
        if ih:H.append({"idx":i,"val":c[i]["h"]})
        if il:L.append({"idx":i,"val":c[i]["l"]})
    return H,L
def detect_coc(c,H,L):
    s=[]
    for i in range(10,len(c)-1):
        rh=[x for x in H if x["idx"]<i][-3:]; rl=[x for x in L if x["idx"]<i][-3:]
        if len(rh)<2 or len(rl)<2: continue
        down=rh[-1]["val"]<rh[-2]["val"] and rl[-1]["val"]<rl[-2]["val"]
        up=rh[-1]["val"]>rh[-2]["val"] and rl[-1]["val"]>rl[-2]["val"]
        if down and c[i]["h"]>rh[-1]["val"] and c[i]["c"]>rh[-1]["val"]:
            s.append({"idx":i,"type":"bull","sl":rl[-1]["val"]})
        if up and c[i]["l"]<rl[-1]["val"] and c[i]["c"]<rl[-1]["val"]:
            s.append({"idx":i,"type":"bear","sl":rh[-1]["val"]})
    return s

def scan_signals(sym,c,cfg,since_ts):
    """BACKFILL: return every valid entry whose entry-candle closed AFTER since_ts.
    This makes the bot robust to skipped/delayed runs — it never misses a signal."""
    H,L=detect_swings(c,LOOKBACK); sigs=detect_coc(c,H,L)
    if not sigs: return []
    liq_r=sorted(x["val"] for x in H); liq_s=sorted((x["val"] for x in L),reverse=True)
    closes=[x["c"] for x in c]
    # arm signals (double confirm)
    prev=None; armed=[]
    for sig in sigs:
        if cfg["DOUBLE_CONFIRM"]:
            if not prev or prev["type"]!=sig["type"] or sig["idx"]-prev["idx"]>20:
                prev=sig; continue
            armed.append(sig); prev=sig
        else:
            armed.append(sig)
    out=[]
    for sig in armed:
        ei=sig["idx"]+1
        if ei>=len(c): continue
        if c[ei]["t"]<=since_ts: continue      # already scanned before
        if cfg["USE_ER"]:
            er=eff_ratio(closes,ei,ER_WINDOW)
            if er is None or er<=cfg["ER_MIN"]: continue
        entry=c[ei]["o"]
        if sig["type"]=="bull":
            sl=sig["sl"]*0.998; risk=entry-sl
            if risk<=0: continue
            above=[v for v in liq_r if v>entry]
            if not above: continue
            if "RR_TARGET" in cfg:
                desired=entry+risk*cfg["RR_TARGET"]; cand=[v for v in above if v>=desired*0.995]
                if not cand: continue
                tgt=cand[0]
            else:
                tgt=above[min(cfg["TARGET_LIQ_IDX"],len(above)-1)]
            rr=(tgt-entry)/risk
            if rr<cfg["MIN_RR"]: continue
            side="BUY"
        else:
            sl=sig["sl"]*1.002; risk=sl-entry
            if risk<=0: continue
            below=[v for v in liq_s if v<entry]
            if not below: continue
            if "RR_TARGET" in cfg:
                desired=entry-risk*cfg["RR_TARGET"]; cand=[v for v in below if v<=desired*1.005]
                if not cand: continue
                tgt=cand[0]
            else:
                tgt=below[min(cfg["TARGET_LIQ_IDX"],len(below)-1)]
            rr=(entry-tgt)/risk
            if rr<cfg["MIN_RR"]: continue
            side="SELL"
        out.append({"symbol":sym,"side":side,"entry_ts":c[ei]["t"],"entry":round(entry,6),
                    "target":round(tgt,6),"sl":round(sl,6),"rr":round(rr,2),
                    "opened_at":datetime.now(timezone.utc).isoformat(),"status":"OPEN"})
    return out

def load_ledger(f):
    if os.path.exists(f):
        with open(f) as fh: return json.load(fh)
    return {"equity":START_EQUITY,"open":[],"closed":[],"last_scan_ts":0}
def save_ledger(f,L):
    with open(f,"w") as fh: json.dump(L,fh,indent=2)
def close_trade(L,tr,result,net_pct,close_ts):
    rp=abs(tr["entry"]-tr["sl"])/tr["entry"]*100; rm=net_pct/rp if rp>0 else 0
    L["equity"]*=(1+rm*RISK_PER_TRADE/100)
    tr=dict(tr); tr.update(status=result,net_pct=round(net_pct,3),r_mult=round(rm,3),
                            closed_ts=close_ts,equity_after=round(L["equity"],2))
    L["closed"].append(tr)
def update_open(L,cbs):
    cost=(FEE_PCT+SLIPPAGE_PCT)*2; keep=[]
    for tr in L["open"]:
        c=cbs.get(tr["symbol"])
        if not c: keep.append(tr); continue
        after=[x for x in c if x["t"]>tr["entry_ts"]]; hit=False
        for x in after:
            if tr["side"]=="BUY":
                if x["l"]<=tr["sl"]: close_trade(L,tr,"LOSS",-(tr["entry"]-tr["sl"])/tr["entry"]*100-cost,x["t"]);hit=True;break
                if x["h"]>=tr["target"]: close_trade(L,tr,"WIN",(tr["target"]-tr["entry"])/tr["entry"]*100-cost,x["t"]);hit=True;break
            else:
                if x["h"]>=tr["sl"]: close_trade(L,tr,"LOSS",-(tr["sl"]-tr["entry"])/tr["entry"]*100-cost,x["t"]);hit=True;break
                if x["l"]<=tr["target"]: close_trade(L,tr,"WIN",(tr["entry"]-tr["target"])/tr["entry"]*100-cost,x["t"]);hit=True;break
        if not hit: keep.append(tr)
    L["open"]=keep
def have(L,sym,ts): return any(t["symbol"]==sym and t["entry_ts"]==ts for t in L["open"]+L["closed"])
def summary(name,L):
    cl=L["closed"]
    if not cl: return f"{name}: 0 closed, {len(L['open'])} open, equity ${L['equity']:,.0f}"
    w=sum(1 for t in cl if t["status"]=="WIN"); n=len(cl)
    wp=[t["net_pct"] for t in cl if t["status"]=="WIN"]; lp=[t["net_pct"] for t in cl if t["status"]=="LOSS"]
    pf=round(sum(wp)/abs(sum(lp)),2) if lp and sum(lp)!=0 else 99.9
    ex=round(sum(t["net_pct"] for t in cl)/n,3)
    return (f"{name}: {n} closed | win {round(w/n*100)}% | PF {pf} | exp {ex:+.3f}% | "
            f"{len(L['open'])} open | equity ${L['equity']:,.0f} ({(L['equity']/START_EQUITY-1)*100:+.1f}%)")

def run(fetch_fn=fetch):
    cbs={}; log=[]
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    log.append(f"=== DUAL PAPER BOT — {stamp} ===")
    for sym in WATCHLIST:
        try: cbs[sym]=fetch_fn(sym,INTERVAL,FETCH_LIMIT)
        except Exception as e: log.append(f"{sym}: fetch failed ({e})")
    for name,cfg in STRATS.items():
        L=load_ledger(cfg["ledger"]); update_open(L,cbs)
        newest_ts=L.get("last_scan_ts",0); max_ts=newest_ts
        for sym in WATCHLIST:
            c=cbs.get(sym)
            if not c or len(c)<ER_WINDOW+20: continue
            has_open_here = any(t["symbol"]==sym for t in L["open"])
            for sig in scan_signals(sym,c,cfg,L.get("last_scan_ts",0)):
                if has_open_here:
                    break  # one open position per symbol at a time (realistic)
                if not have(L,sym,sig["entry_ts"]):
                    L["open"].append(sig); has_open_here=True
                    et=datetime.fromtimestamp(sig["entry_ts"]/1000,timezone.utc).strftime("%m-%d %H:%M")
                    log.append(f"[{name}] NEW {sig['side']} {sym} @ {sig['entry']:.4f} tgt {sig['target']:.4f} sl {sig['sl']:.4f} RR {sig['rr']} ({et})")
                max_ts=max(max_ts,sig["entry_ts"])
            if c: max_ts=max(max_ts,c[-1]["t"])
        L["last_scan_ts"]=max_ts
        save_ledger(cfg["ledger"],L); cfg["_L"]=L
    for name,cfg in STRATS.items(): log.append(summary(name,cfg["_L"]))
    out="\n".join(log)
    print(out)
    # also write a human-readable status file for phone viewing
    with open("STATUS.txt","w") as f: f.write(out+"\n")
    return out

if __name__=="__main__": run()
