import os
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="코로나 이후 영화 산업의 변화와 장르별 타격 분석",
    page_icon="🎬",
    layout="wide"
)

PRE_YEARS = [2017, 2018, 2019]
POST_YEARS = [2023, 2024, 2025]

FILE_MARKET = "market_overview.csv"
FILE_GENRE  = "genre_analysis.csv"
FILE_ONLINE = "online_stats.csv"

# =========================
# Utils
# =========================
def _clean_col(c: str) -> str:
    return re.sub(r"\s+", "", str(c)).strip()

def _to_number(x):
    if pd.isna(x):
        return np.nan
    s = str(x).replace(",", "").replace(" ", "")
    s = re.sub(r"[^\d\.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return np.nan
    try:
        return float(s)
    except:
        return np.nan

def _find_col(df, patterns):
    cols = list(df.columns)
    cleaned = {c: _clean_col(c) for c in cols}
    for p in patterns:
        try:
            rgx = re.compile(p)
            for c in cols:
                if rgx.search(cleaned[c]):
                    return c
        except:
            for c in cols:
                if p in cleaned[c]:
                    return c
    return None

def _pct_change(pre, post):
    if pd.isna(pre) or pre == 0 or pd.isna(post):
        return np.nan
    return (post - pre) / pre

def _fmt_pct(x):
    if pd.isna(x): return "NA"
    return f"{x*100:+.1f}%"

def _fmt_int(x):
    if pd.isna(x): return "NA"
    try:
        return f"{int(round(float(x))):,}"
    except:
        return str(x)

def _fmt_money(x):
    if pd.isna(x): return "NA"
    try:
        return f"{float(x):,.0f}"
    except:
        return str(x)

def _period_label(y: int) -> str:
    y = int(y)
    if y in PRE_YEARS:
        return "코로나 전"
    if y in POST_YEARS:
        return "코로나 후"
    return "기타"

def _safe_pct_text(v):
    return "NA" if pd.isna(v) else f"{v*100:+.1f}%"

def _safe_pp_text(v):
    return "NA" if pd.isna(v) else f"{v*100:+.2f}%p"

# =========================
# Charts
# =========================
def _thin_barh(df, x, y, title, x_is_pct=True, height=720):
    d = df.copy()
    if x_is_pct:
        d["_text"] = d[x].apply(lambda v: "" if pd.isna(v) else f"{v*100:+.1f}%")
    else:
        d["_text"] = d[x].apply(lambda v: "" if pd.isna(v) else f"{v:,.0f}")

    fig = px.bar(
        d, x=x, y=y,
        orientation="h",
        title=title,
        template="plotly_white",
        text="_text",
        color=x,
        color_continuous_scale="RdYlGn"
    )
    fig.update_layout(
        height=height,
        bargap=0.78,
        margin=dict(l=10, r=90, t=80, b=10),
        coloraxis_showscale=False,
        uniformtext_minsize=12,
        uniformtext_mode="show",
        title_font_size=20
    )
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=14)
    fig.update_xaxes(tickformat=".0%" if x_is_pct else ",", title=None)
    fig.update_yaxes(title=None)
    st.plotly_chart(fig, use_container_width=True)

def _line(df, x, y, color, title, height=460):
    fig = px.line(
        df, x=x, y=y,
        color=color,
        markers=True,
        template="plotly_white",
        title=title
    )
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=80, b=10),
        title_font_size=20
    )
    fig.update_xaxes(tickmode="linear", title=None)
    fig.update_yaxes(tickformat=",", title=None)
    st.plotly_chart(fig, use_container_width=True)

def _group_bar_pct(df, x, y, color, title, height=520):
    d = df.copy()
    d["_text"] = d[y].apply(lambda v: "" if pd.isna(v) else f"{v*100:+.1f}%")
    fig = px.bar(
        d, x=x, y=y,
        color=color,
        barmode="group",
        title=title,
        template="plotly_white",
        text="_text"
    )
    fig.update_layout(
        height=height,
        bargap=0.60,
        bargroupgap=0.55,
        margin=dict(l=10, r=10, t=80, b=10),
        uniformtext_minsize=12,
        uniformtext_mode="show",
        title_font_size=20
    )
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=14)
    fig.update_yaxes(tickformat=".0%", title=None)
    fig.update_xaxes(title=None)
    st.plotly_chart(fig, use_container_width=True)

def _scatter_with_lines(df, x, y, text, title, vline=None, hline=None, height=650):
    fig = px.scatter(
        df, x=x, y=y,
        text=text,
        hover_name=text,
        template="plotly_white",
        title=title
    )
    fig.update_traces(textposition="top center", textfont_size=13)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=80, b=10), title_font_size=20)
    fig.update_xaxes(
    tickformat=".0%",
    title="오프라인 관객 변화율")
    fig.update_yaxes(
    tickformat=".0%",
    title="온라인 점유율 변화")


    if vline is not None:
        fig.add_vline(x=vline, line_width=2, line_dash="dash")
    if hline is not None:
        fig.add_hline(y=hline, line_width=2, line_dash="dash")

    st.plotly_chart(fig, use_container_width=True)

# =========================
# Loaders
# =========================
@st.cache_data(show_spinner=False)
def load_market():
    if not os.path.exists(FILE_MARKET):
        return None, f"{FILE_MARKET} 파일을 찾을 수 없습니다."
    df = pd.read_csv(FILE_MARKET)

    year_col  = _find_col(df, [r"연도", r"year"])
    scope_col = _find_col(df, [r"범주", r"구분", r"scope", r"type", r"category"])
    sales_col = _find_col(df, [r"매출", r"sales", r"revenue"])
    audi_col  = _find_col(df, [r"관객", r"aud", r"audience"])
    scrn_col  = _find_col(df, [r"스크린", r"상영", r"screen", r"show"])

    if year_col is None or scope_col is None or sales_col is None or audi_col is None:
        return None, f"{FILE_MARKET} 컬럼 인식 실패"

    out = df.rename(columns={
        year_col: "연도",
        scope_col: "범주",
        sales_col: "매출액",
        audi_col: "관객수",
        scrn_col: "스크린수" if scrn_col else scrn_col
    }).copy()

    out["연도"] = out["연도"].apply(_to_number).astype("Int64")
    out["매출액"] = out["매출액"].apply(_to_number)
    out["관객수"] = out["관객수"].apply(_to_number)
    out["스크린수"] = out["스크린수"].apply(_to_number) if scrn_col else np.nan

    out["범주"] = out["범주"].astype(str).str.replace(" ", "")
    out["범주"] = out["범주"].replace({
        "전체(국산+해외)": "전체",
        "전체(국산+외화)": "전체",
        "국산영화": "국산",
        "한국영화": "국산",
        "국내": "국산"
    })

    out = out[out["연도"].isin(PRE_YEARS + POST_YEARS)].copy()
    return out, None

@st.cache_data(show_spinner=False)
def load_genre():
    if not os.path.exists(FILE_GENRE):
        return None, f"{FILE_GENRE} 파일을 찾을 수 없습니다."
    df = pd.read_csv(FILE_GENRE)

    year_col  = _find_col(df, [r"연도", r"year"])
    genre_col = _find_col(df, [r"장르", r"genre"])
    scope_col = _find_col(df, [r"범주", r"구분", r"type", r"category"])
    sales_col = _find_col(df, [r"매출", r"sales", r"revenue"])
    audi_col  = _find_col(df, [r"관객", r"aud", r"audience"])
    scrn_col  = _find_col(df, [r"스크린", r"상영", r"screen", r"show"])

    if year_col is None or genre_col is None or sales_col is None or audi_col is None:
        return None, f"{FILE_GENRE} 컬럼 인식 실패"

    out = df.rename(columns={
        year_col: "연도",
        genre_col: "장르",
        scope_col: "범주" if scope_col else scope_col,
        sales_col: "매출액",
        audi_col: "관객수",
        scrn_col: "스크린수" if scrn_col else scrn_col
    }).copy()

    out["연도"] = out["연도"].apply(_to_number).astype("Int64")
    out["장르"] = out["장르"].astype(str).str.strip()
    out["매출액"] = out["매출액"].apply(_to_number)
    out["관객수"] = out["관객수"].apply(_to_number)
    out["스크린수"] = out["스크린수"].apply(_to_number) if scrn_col else np.nan

    if scope_col:
        out["범주"] = out["범주"].astype(str).str.replace(" ", "")
        out["범주"] = out["범주"].replace({
            "전체(국산+해외)": "전체",
            "전체(국산+외화)": "전체",
            "국산영화": "국산",
            "한국영화": "국산",
            "국내": "국산"
        })
    else:
        out["범주"] = "전체"

    out = out[out["연도"].isin(PRE_YEARS + POST_YEARS)].copy()
    return out, None

@st.cache_data(show_spinner=False)
def load_online():
    if not os.path.exists(FILE_ONLINE):
        return None, f"{FILE_ONLINE} 파일을 찾을 수 없습니다."
    df = pd.read_csv(FILE_ONLINE)

    year_col  = _find_col(df, [r"연도", r"year"])
    genre_col = _find_col(df, [r"장르", r"genre"])
    share_col = _find_col(df, [r"점유율", r"share", r"비중"])

    if year_col is None or genre_col is None or share_col is None:
        return None, f"{FILE_ONLINE} 컬럼 인식 실패"

    out = df.rename(columns={year_col:"연도", genre_col:"장르", share_col:"점유율"}).copy()
    out["연도"] = out["연도"].apply(_to_number).astype("Int64")
    out["장르"] = out["장르"].astype(str).str.strip()
    out["점유율"] = out["점유율"].apply(_to_number)

    if out["점유율"].dropna().max() > 1.5:
        out["점유율"] = out["점유율"] / 100.0

    out = out[out["연도"].isin(PRE_YEARS + POST_YEARS)].copy()
    return out, None

# =========================
# Indicators
# =========================
@st.cache_data(show_spinner=False)
def build_market_indicators(df_market):
    year_sum = df_market.groupby(["연도","범주"], as_index=False)[["매출액","관객수","스크린수"]].sum()
    year_sum["기간"] = year_sum["연도"].apply(_period_label)

    period_avg = year_sum.groupby(["기간","범주"], as_index=False)[["매출액","관객수","스크린수"]].mean(numeric_only=True)

    rows = []
    for scope in sorted(period_avg["범주"].unique()):
        pre = period_avg[(period_avg["범주"]==scope) & (period_avg["기간"]=="코로나 전")]
        post= period_avg[(period_avg["범주"]==scope) & (period_avg["기간"]=="코로나 후")]
        if pre.empty or post.empty:
            continue
        pre = pre.iloc[0]; post = post.iloc[0]
        rows.append({
            "범주": scope,
            "매출액_전": pre["매출액"], "매출액_후": post["매출액"], "매출액_증감률": _pct_change(pre["매출액"], post["매출액"]),
            "관객수_전": pre["관객수"], "관객수_후": post["관객수"], "관객수_증감률": _pct_change(pre["관객수"], post["관객수"]),
            "스크린수_전": pre["스크린수"], "스크린수_후": post["스크린수"], "스크린수_증감률": _pct_change(pre["스크린수"], post["스크린수"]),
        })

    return year_sum, period_avg, pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def build_genre_indicators(df_genre):
    df = df_genre.copy()
    df["기간"] = df["연도"].apply(_period_label)
    agg = df.groupby(["기간","범주","장르"], as_index=False)[["매출액","관객수","스크린수"]].mean(numeric_only=True)

    rows = []
    for scope in sorted(agg["범주"].unique()):
        for g in sorted(agg["장르"].unique()):
            pre = agg[(agg["범주"]==scope) & (agg["장르"]==g) & (agg["기간"]=="코로나 전")]
            post= agg[(agg["범주"]==scope) & (agg["장르"]==g) & (agg["기간"]=="코로나 후")]
            if pre.empty or post.empty:
                continue
            pre = pre.iloc[0]; post = post.iloc[0]
            rows.append({
                "범주": scope,
                "장르": g,
                "관객수_증감률": _pct_change(pre["관객수"], post["관객수"]),
                "매출액_증감률": _pct_change(pre["매출액"], post["매출액"]),
                "스크린수_증감률": _pct_change(pre["스크린수"], post["스크린수"]),
            })
    return agg, pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def build_online_indicators(df_online):
    df = df_online.copy()
    df["기간"] = df["연도"].apply(_period_label)
    period_avg = df.groupby(["기간","장르"], as_index=False)["점유율"].mean()

    rows = []
    for g in sorted(period_avg["장르"].unique()):
        pre = period_avg[(period_avg["장르"]==g) & (period_avg["기간"]=="코로나 전")]
        post= period_avg[(period_avg["장르"]==g) & (period_avg["기간"]=="코로나 후")]
        if pre.empty or post.empty:
            continue
        pre_v = float(pre.iloc[0]["점유율"])
        post_v = float(post.iloc[0]["점유율"])
        rows.append({
            "장르": g,
            "점유율_전": pre_v,
            "점유율_후": post_v,
            "점유율_변화": post_v - pre_v,
        })

    return period_avg, pd.DataFrame(rows)

def _recommend_rule(offline_change, online_delta, x_thr, y_thr):
    if pd.isna(offline_change):
        return "재검토"
    if (offline_change <= x_thr) and (not pd.isna(online_delta)) and (online_delta >= y_thr):
        return "OTT"
    if offline_change > x_thr:
        return "극장"
    return "추가 검토"

# =========================
# Auto memos (그래프 결과 요약)
# =========================
def market_memo(m_change: pd.DataFrame) -> str:
    if m_change is None or m_change.empty:
        return "요약 생성 불가"
    d = m_change.set_index("범주")
    if ("전체" not in d.index) or ("국산" not in d.index):
        # 한 종류만 있을 때
        k = d.index[0]
        s = d.loc[k]
        return f"{k} 매출 변화율 {_safe_pct_text(s['매출액_증감률'])}, 관객 변화율 {_safe_pct_text(s['관객수_증감률'])}"
    all_s = d.loc["전체"]
    kor_s = d.loc["국산"]

    sales_gap = kor_s["매출액_증감률"] - all_s["매출액_증감률"]
    aud_gap   = kor_s["관객수_증감률"] - all_s["관객수_증감률"]

    sales_rel = "국산 감소폭이 더 큼" if (not pd.isna(sales_gap) and sales_gap < 0) else "국산 감소폭이 더 작음"
    aud_rel   = "국산 감소폭이 더 큼" if (not pd.isna(aud_gap) and aud_gap < 0) else "국산 감소폭이 더 작음"

    return (
        f"매출 변화율 전체 {_safe_pct_text(all_s['매출액_증감률'])}, 국산 {_safe_pct_text(kor_s['매출액_증감률'])}, {sales_rel}. "
        f"관객 변화율 전체 {_safe_pct_text(all_s['관객수_증감률'])}, 국산 {_safe_pct_text(kor_s['관객수_증감률'])}, {aud_rel}."
    )

def genre_memo(tmp: pd.DataFrame) -> str:
    if tmp is None or tmp.empty:
        return "요약 생성 불가"

    d = tmp.dropna(subset=["관객수_증감률"]).copy()
    if len(d) < 4:
        return "장르별 비교를 위한 데이터가 충분하지 않다."

    # 감소폭 큰 장르 2개
    worst = d.nsmallest(2, "관객수_증감률")[["장르","관객수_증감률"]].values.tolist()
    # 감소폭 작은 장르 2개
    best  = d.nlargest(2, "관객수_증감률")[["장르","관객수_증감률"]].values.tolist()

    w1, w2 = worst
    b1, b2 = best

    return (
        f"{w1[0]}와 {w2[0]} 장르는 관객 변화율이 각각 "
        f"{_safe_pct_text(w1[1])}, {_safe_pct_text(w2[1])}로 나타나 "
        f"분석 대상 장르 중 감소폭이 가장 큰 것으로 확인된다. "
        f"반면 {b1[0]}와 {b2[0]} 장르는 "
        f"{_safe_pct_text(b1[1])}, {_safe_pct_text(b2[1])} 수준으로 "
        f"상대적으로 관객 감소가 제한적인 장르로 분류된다."
    )


def online_memo(o_change: pd.DataFrame) -> str:
    if o_change is None or o_change.empty:
        return "요약 생성 불가"
    d = o_change.dropna(subset=["점유율_변화"]).copy()
    if d.empty:
        return "요약 생성 불가"
    down = d.nsmallest(2, "점유율_변화")[["장르","점유율_변화"]].values.tolist()
    up   = d.nlargest(2, "점유율_변화")[["장르","점유율_변화"]].values.tolist()
    dn_txt = ", ".join([f"{g} {_safe_pp_text(v)}" for g, v in down])
    up_txt = ", ".join([f"{g} {_safe_pp_text(v)}" for g, v in up])
    return f"점유율 하락 상위 {dn_txt}. 점유율 상승 상위 {up_txt}."

def strategy_memo(summary_df: pd.DataFrame) -> str:
    if summary_df is None or summary_df.empty or "제언" not in summary_df.columns:
        return "요약 생성 불가"
    cnt = summary_df["제언"].value_counts().to_dict()
    ott = cnt.get("OTT", 0)
    th  = cnt.get("극장", 0)
    ex  = cnt.get("추가 검토", 0)
    re  = cnt.get("재검토", 0)
    return f"제언 분류 결과 OTT {ott}개, 극장 {th}개, 추가 검토 {ex}개, 재검토 {re}개."

# =========================
# Load data
# =========================
df_market, err = load_market()
if err: st.error(err); st.stop()

df_genre, err = load_genre()
if err: st.error(err); st.stop()

df_online, err = load_online()
if err: st.error(err); st.stop()

m_year, m_period, m_change = build_market_indicators(df_market)
g_agg, g_change = build_genre_indicators(df_genre)
o_period, o_change = build_online_indicators(df_online)

# =========================
# Summary table
# =========================
base_scope = "국산" if "국산" in g_change["범주"].unique() else "전체"
base_label = "국산 영화 기준" if base_scope == "국산" else "전체 기준"

summary_df = pd.DataFrame()
x_thr = None
y_thr = None

if not o_change.empty:
    off = g_change[g_change["범주"]==base_scope][["장르","관객수_증감률","매출액_증감률"]].copy()
    merged = off.merge(o_change[["장르","점유율_변화"]], on="장르", how="left").dropna()
    if not merged.empty:
        x_thr = float(merged["관객수_증감률"].quantile(0.33))
        y_thr = float(merged["점유율_변화"].median())
        merged["제언"] = merged.apply(lambda r: _recommend_rule(r["관객수_증감률"], r["점유율_변화"], x_thr, y_thr), axis=1)
        summary_df = merged.rename(columns={
            "관객수_증감률": "오프라인 관객 변화율",
            "매출액_증감률": "오프라인 매출 변화율",
            "점유율_변화": "온라인 점유율 변화"
        }).copy()

# =========================
# Navigation
# =========================
st.sidebar.title("목차")
page = st.sidebar.radio(
    "파트 선택",
    ["연구배경 및 필요성", "프로젝트 진행과정", "자료 해석", "프로젝트 성과", "프로젝트 기대효과"],
    index=0
)

st.title("코코로나 이후 영화 산업의 변화와 장르별 타격 분석")
st.caption("코로나 전 2017–2019 | 코로나 후 2023–2025")

# =========================
# Pages
# =========================
if page == "연구배경 및 필요성":
    st.markdown("## 연구배경 및 필요성")
    st.markdown("""
코로나19 이후 영화 티켓 가격이 상승하면서 관람 비용이 증가하였다. 관람 비용 증가는 수요 감소로 이어질 수 있으며, 이는 관객수 감소로 확인된다. 매출액은 티켓 단가 상승 효과가 포함되므로, 시장 변화는 매출액과 관객수를 함께 비교하여 판단한다. 본 프로젝트는 코로나 전과 코로나 후를 비교하여 영화산업의 규모 변화와 수요 변화가 동시에 발생했는지 확인한다.  

또한 전체 시장과 국산 영화 시장의 충격은 동일하지 않을 수 있다. 전체 시장은 해외 흥행작 성과로 일부 완충될 수 있으나, 국산 영화는 관객 이탈의 영향을 더 크게 받을 수 있다. 따라서 동일한 비교 구간에서 국산의 감소폭이 더 큰지 여부를 별도로 확인한다.  

시장 쇠퇴가 확인되더라도 장르별 충격은 다르게 나타난다. 본 프로젝트는 수집한 10개 장르를 기준으로 장르별 타격 정도를 변화율 중심으로 비교하고, 결과를 바탕으로 장르별 개봉 전략을 제안한다.
""")
    st.info("메모: 분석 흐름은 시장 변화 확인 후 장르별 타격을 중심으로 정리한다.")

elif page == "프로젝트 진행과정":
    st.markdown("## 프로젝트 진행과정")

    st.markdown("### 데이터 수집")
    st.markdown("""
- KOBIS 영화관입장권통합전산망에서 연도별 박스오피스 데이터를 수집하였다. 
https://www.kobis.or.kr/kobis/business/stat/boxs/findYearlyBoxOfficeList.do?loadEnd=0&searchType=search&sSearchYearFrom={year}&sMultiMovieYn=N&sRepNationCd={nation_code} 
- 전체와 국산을 구분하여 2017–2019, 2023–2025 연도별 상위 영화 데이터를 확보하였다.  
- 장르별 분석을 위해 주요 장르를 기준으로 별도 조회하여 장르별 흥행 데이터를 확보하였다.  
- VKOBIS 온라인상영관통합전산망에서 장르별 온라인 이용 점유율 데이터를 수집하였다.                                                                 
https://www.vkobis.or.kr/statistics/selectGenreList.do
""")

    st.markdown("### 수집 방식")
    st.markdown("""
- Selenium 기반 자동화를 통해 페이지 로딩 대기, 테이블 요소 탐색, 상위 N개 행 추출, CSV 저장 과정을 수행하였다.
""")

    st.info("메모: 아래 코드는 market_overview.csv 생성에 사용한 수집 코드 일부 발췌이다.")

    excerpt = r'''
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def scrape_market_overview():
    years = [2017, 2018, 2019, 2023, 2024, 2025]
    result_data = []

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()

    try:
        wait = WebDriverWait(driver, 15)

        for year in years:
            for category_name, nation_code in [("전체", ""), ("국산", "K")]:
                url = f"https://www.kobis.or.kr/kobis/business/stat/boxs/findYearlyBoxOfficeList.do?loadEnd=0&searchType=search&sSearchYearFrom={year}&sMultiMovieYn=N&sRepNationCd={nation_code}"
                driver.get(url)

                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbl_comm tbody tr")))
                time.sleep(2)

                rows = driver.find_elements(By.CSS_SELECTOR, "table.tbl_comm tbody tr")

                count = 0
                for row in rows:
                    if count >= 25: break

                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 8: continue

                    title = row.find_element(By.CSS_SELECTOR, "span.txt_ellip").text.strip()
                    revenue = cols[3].text.replace(",", "").strip()
                    audience = cols[5].text.replace(",", "").strip()
                    screens = cols[7].text.replace(",", "").strip()

                    result_data.append({
                        "범주": category_name,
                        "연도": year,
                        "순위": count + 1,
                        "영화명": title,
                        "매출액": int(revenue) if revenue.isdigit() else 0,
                        "관객수": int(audience) if audience.isdigit() else 0,
                        "스크린수": int(screens) if screens.isdigit() else 0
                    })
                    count += 1

        df = pd.DataFrame(result_data)
        df.to_csv("market_overview.csv", index=False, encoding="utf-8-sig")

    finally:
        driver.quit()
'''
    st.code(excerpt.strip(), language="python")

elif page == "자료 해석":
    st.markdown("## 자료 해석")

    # =========================
    # 시장 비교
    # =========================
    st.markdown("### 시장 비교")

    if not m_change.empty:
        show = m_change.copy()
        show["매출액_전"] = show["매출액_전"].apply(_fmt_money)
        show["매출액_후"] = show["매출액_후"].apply(_fmt_money)
        show["매출액_증감률"] = show["매출액_증감률"].apply(_fmt_pct)
        show["관객수_전"] = show["관객수_전"].apply(_fmt_int)
        show["관객수_후"] = show["관객수_후"].apply(_fmt_int)
        show["관객수_증감률"] = show["관객수_증감률"].apply(_fmt_pct)

        st.dataframe(
            show[["범주","매출액_전","매출액_후","매출액_증감률","관객수_전","관객수_후","관객수_증감률"]]
            .rename(columns={
                "범주":"구분",
                "매출액_전":"매출액 코로나 전",
                "매출액_후":"매출액 코로나 후",
                "매출액_증감률":"매출 변화율",
                "관객수_전":"관객수 코로나 전",
                "관객수_후":"관객수 코로나 후",
                "관객수_증감률":"관객 변화율",
            }),
            use_container_width=True
        )

        melt = []
        for _, r in m_change.iterrows():
            melt += [
                {"구분": r["범주"], "지표":"매출액", "변화율": r["매출액_증감률"]},
                {"구분": r["범주"], "지표":"관객수", "변화율": r["관객수_증감률"]},
            ]
        melt = pd.DataFrame(melt)
        _group_bar_pct(melt, x="지표", y="변화율", color="구분", title="시장 변화율")

        st.info(f"메모: {market_memo(m_change)}")

    st.markdown("### 연도별 추세")
    _line(m_year.sort_values(["범주","연도"]), "연도", "관객수", "범주", "관객수 추세")
    # 연도별 추세 요약: 최근(2025) vs 2019 비교(가능하면)
    try:
        y19 = m_year[m_year["연도"]==2019].set_index("범주")["관객수"]
        y25 = m_year[m_year["연도"]==2025].set_index("범주")["관객수"]
        if ("전체" in y19.index) and ("전체" in y25.index):
            msg = f"전체 관객수는 2019년 {_fmt_int(y19['전체'])}에서 2025년 {_fmt_int(y25['전체'])}로 변화"
            if ("국산" in y19.index) and ("국산" in y25.index):
                msg += f", 국산은 2019년 {_fmt_int(y19['국산'])}에서 2025년 {_fmt_int(y25['국산'])}로 변화"
            st.info(f"메모: {msg}.")
    except:
        pass

    _line(m_year.sort_values(["범주","연도"]), "연도", "매출액", "범주", "매출액 추세")
    try:
        y19s = m_year[m_year["연도"]==2019].set_index("범주")["매출액"]
        y25s = m_year[m_year["연도"]==2025].set_index("범주")["매출액"]
        if ("전체" in y19s.index) and ("전체" in y25s.index):
            msg = f"전체 매출액은 2019년 {_fmt_money(y19s['전체'])}에서 2025년 {_fmt_money(y25s['전체'])}로 변화"
            if ("국산" in y19s.index) and ("국산" in y25s.index):
                msg += f", 국산은 2019년 {_fmt_money(y19s['국산'])}에서 2025년 {_fmt_money(y25s['국산'])}로 변화"
            st.info(f"메모: {msg}.")
    except:
        pass

    st.divider()

    # =========================
    # 장르별 타격 비교
    # =========================
    st.markdown("### 장르별 타격 비교")

    order = []
    if "전체" in g_change["범주"].unique(): order.append("전체")
    if "국산" in g_change["범주"].unique(): order.append("국산")
    for s in sorted(g_change["범주"].unique()):
        if s not in order:
            order.append(s)

    for scope in order:
        tmp = g_change[g_change["범주"]==scope].copy().sort_values("관객수_증감률")
        st.markdown(f"#### {scope}")

        tab = tmp.copy()
        tab["관객수_증감률"] = tab["관객수_증감률"].apply(_fmt_pct)
        tab["매출액_증감률"] = tab["매출액_증감률"].apply(_fmt_pct)
        st.dataframe(
            tab[["장르","관객수_증감률","매출액_증감률"]]
            .rename(columns={"관객수_증감률":"관객 변화율","매출액_증감률":"매출 변화율"}),
            use_container_width=True, height=420
        )

        _thin_barh(tmp, "관객수_증감률", "장르", f"{scope} 장르 관객 변화율")
        st.info(f"메모: {genre_memo(tmp)}")

    st.divider()

    # =========================
    # 온라인
    # =========================
    st.markdown("### 장르별 온라인 타격 비교")

    if not o_change.empty:
        o_sorted = o_change.sort_values("점유율_변화")
        show = o_sorted.copy()
        show["점유율_전"] = show["점유율_전"].map(lambda v: f"{v*100:.2f}%")
        show["점유율_후"] = show["점유율_후"].map(lambda v: f"{v*100:.2f}%")
        show["점유율_변화"] = show["점유율_변화"].map(lambda v: f"{v*100:+.2f}%p")
        st.dataframe(
            show.rename(columns={"점유율_전":"점유율 코로나 전","점유율_후":"점유율 코로나 후","점유율_변화":"점유율 변화"}),
            use_container_width=True, height=420
        )

        tmp = o_sorted.copy()
        _thin_barh(tmp, "점유율_변화", "장르", "온라인 점유율 변화")
        st.info(f"메모: {online_memo(o_change)}")

        if not summary_df.empty and x_thr is not None and y_thr is not None:
            st.markdown("### 개봉 전략 구분")
            st.info(
                "메모: 기준선은 오프라인 관객 변화율 하위 33% 지점과 온라인 점유율 변화 중앙값으로 설정"
            )

            plot_df = summary_df.rename(columns={
                "오프라인 관객 변화율": "offline",
                "온라인 점유율 변화": "online"
            })[["장르","offline","online"]].copy()

            _scatter_with_lines(
                plot_df,
                x="offline", y="online", text="장르",
                title=f"{base_label} 오프라인 관객 변화율과 온라인 점유율 변화",
                vline=x_thr, hline=y_thr
            )
            st.info(f"메모: {strategy_memo(summary_df)}")

            st.markdown("### 정리 표")
            out = summary_df.copy()
            out["오프라인 관객 변화율"] = out["오프라인 관객 변화율"].apply(_fmt_pct)
            out["오프라인 매출 변화율"] = out["오프라인 매출 변화율"].apply(_fmt_pct)
            out["온라인 점유율 변화"] = out["온라인 점유율 변화"].apply(lambda v: "NA" if pd.isna(v) else f"{v*100:+.2f}%p")
            out = out[["장르","오프라인 관객 변화율","오프라인 매출 변화율","온라인 점유율 변화","제언"]].copy()

            order_map = {"OTT":0, "극장":1, "추가 검토":2, "재검토":3}
            out["_o"] = out["제언"].map(order_map).fillna(9)
            out = out.sort_values(["_o","장르"]).drop(columns=["_o"])

            st.dataframe(out, use_container_width=True, height=520)

    else:
        st.warning("online_stats.csv에서 점유율 데이터를 충분히 읽지 못했습니다.")

elif page == "프로젝트 성과":
    st.markdown("## 프로젝트 성과")
    st.markdown("""
본 프로젝트는 코로나 전과 코로나 후 구간을 기준으로 영화 산업의 수요와 규모가 동시에 약화되었는지 여부를 시장 지표로 확인하고, 그 충격이 장르별로 어떻게 분화되는지까지 연결하여 정리하였다. 시장 단계에서는 매출과 관객을 함께 비교함으로써 티켓 가격 상승 효과가 포함된 매출 지표를 단독으로 해석하지 않고, 실제 수요 기반의 변화가 동반되었는지를 검증하였다. 또한 동일한 비교 구간에서 전체와 국산을 분리하여 확인함으로써 국산 시장의 취약성이 상대적으로 더 크게 나타나는지 여부를 점검할 수 있도록 구성하였다.  

장르 단계에서는 동일한 시장 충격이 장르별로 균질하게 나타나지 않는다는 점에 초점을 두고, 수집된 주요 장르를 기준으로 관객 변화율과 매출 변화율을 동시에 제시하였다. 이를 통해 특정 장르는 극장 수요 감소가 집중되는 반면, 일부 장르는 상대적으로 방어되는 양상이 확인될 수 있으며, 장르별로 개봉 전략을 분리해야 하는 근거를 확보하였다.  

마지막으로 온라인 점유율 변화를 결합하여 극장에서 타격이 큰 장르 중 온라인에서의 구조적 변화가 제한적인 장르를 식별하고, 채널 전환 전략을 제언 가능한 형태로 정리하였다. 아래 표는 자료 해석 단계에서 도출된 장르별 지표와 제언 결과를 요약한 것이다.
""")
    if not summary_df.empty:
        out = summary_df.copy()
        out["오프라인 관객 변화율"] = out["오프라인 관객 변화율"].apply(_fmt_pct)
        out["오프라인 매출 변화율"] = out["오프라인 매출 변화율"].apply(_fmt_pct)
        out["온라인 점유율 변화"] = out["온라인 점유율 변화"].apply(lambda v: "NA" if pd.isna(v) else f"{v*100:+.2f}%p")
        out = out[["장르","오프라인 관객 변화율","오프라인 매출 변화율","온라인 점유율 변화","제언"]].copy()
        st.dataframe(out, use_container_width=True, height=520)
    else:
        st.info("온라인 결합 요약표 생성 불가")

elif page == "프로젝트 기대효과":
    st.markdown("## 프로젝트 기대효과")
    st.markdown("""
본 분석은 영화 산업의 변화가 단일 지표로 설명되지 않는다는 점을 전제로, 시장 지표와 장르 지표를 연결하여 전략적 의사결정에 바로 활용 가능한 형태로 정리했다는 점에서 기대효과가 있다. 첫째, 장르별 관객 변화율을 기반으로 극장 개봉 리스크가 높은 장르와 상대적으로 유지되는 장르를 구분할 수 있어, 제작·배급 단계에서 창구 전략을 장르 단위로 설계할 수 있다. 둘째, 온라인 점유율 변화를 결합하면 극장 타격이 큰 장르 중에서도 온라인에서 상대적 선호 구조가 유지되는 장르를 식별할 수 있어, 극장 중심 전략 대신 OTT 공개 전략으로 전환하는 근거를 제공할 수 있다.  

셋째, 전체와 국산을 분리하여 비교한 구조는 국산 시장이 어떤 구간에서 더 취약한지를 장르 단위로 점검하는 데 활용될 수 있다. 이는 국산 영화 산업의 포트폴리오 재구성, 투자 우선순위 조정, 배급 전략 재설계에 실무적으로 연결될 수 있는 형태의 결과물이다. 아래 요약표는 장르별 지표와 제언 결과를 기준으로, 개봉 채널 전략을 정리하는 데 바로 활용할 수 있다.
""")

    if not summary_df.empty:
        out = summary_df.copy()
        out["오프라인 관객 변화율"] = out["오프라인 관객 변화율"].apply(_fmt_pct)
        out["온라인 점유율 변화"] = out["온라인 점유율 변화"].apply(lambda v: "NA" if pd.isna(v) else f"{v*100:+.2f}%p")
        out = out[["장르","오프라인 관객 변화율","온라인 점유율 변화","제언"]].copy()

        order_map = {"OTT":0, "극장":1, "추가 검토":2, "재검토":3}
        out["_o"] = out["제언"].map(order_map).fillna(9)
        out = out.sort_values(["_o","장르"]).drop(columns=["_o"])

        st.dataframe(out, use_container_width=True, height=520)
    else:
        st.info("요약표 생성 불가")


