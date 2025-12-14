%%writefile movie.py
import os
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# Page setup
# =========================
st.set_page_config(
    page_title="티켓플레이션 시대, 국산 영화 생존 전략",
    page_icon="🎬",
    layout="wide"
)

PRE_YEARS = [2017, 2018, 2019]
POST_YEARS = [2023, 2024, 2025]

FILE_MARKET = "market_overview.csv"
FILE_GENRE  = "genre_analysis.csv"
FILE_ONLINE = "online_stats.csv"

EXCLUDE_GENRES = {"애니메이션"}  # <- 애니메이션 완전 제외

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
    if pd.isna(x):
        return "NA"
    return f"{x*100:+.1f}%"

def _fmt_pp(x):
    if pd.isna(x):
        return "NA"
    return f"{x*100:+.2f}%p"

def _fmt_int(x):
    if pd.isna(x):
        return "NA"
    try:
        return f"{int(round(float(x))):,}"
    except:
        return str(x)

def _fmt_money(x):
    if pd.isna(x):
        return "NA"
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

def _norm_genre(s: str) -> str:
    """
    장르명 표기 흔들림 정리.
    (애니메이션은 이후 단계에서 완전히 제외)
    """
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = s.replace(" ", "")
    s = s.replace("／", "/").replace("∕", "/")
    s = s.replace("멜로로맨스", "멜로/로맨스")
    s = s.replace("멜로/로멘스", "멜로/로맨스")
    if s == "애니":
        s = "애니메이션"
    return s

# =========================
# Charts
# =========================
def _thin_barh(df, x, y, title, x_is_pct=True, height=700):
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
        bargap=0.78,  # 날씬한 막대
        margin=dict(l=10, r=110, t=90, b=10),
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
        margin=dict(l=10, r=10, t=90, b=10),
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
        margin=dict(l=10, r=10, t=90, b=10),
        uniformtext_minsize=12,
        uniformtext_mode="show",
        title_font_size=20
    )
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=14)
    fig.update_yaxes(tickformat=".0%", title=None)
    fig.update_xaxes(title=None)
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
    out["장르"] = out["장르"].apply(_norm_genre)
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

    # 애니메이션 완전 제외
    out = out[~out["장르"].isin(EXCLUDE_GENRES)].copy()

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
    out["장르"] = out["장르"].apply(_norm_genre)
    out["점유율"] = out["점유율"].apply(_to_number)

    if out["점유율"].dropna().max() > 1.5:
        out["점유율"] = out["점유율"] / 100.0

    out = out[out["연도"].isin(PRE_YEARS + POST_YEARS)].copy()

    # 애니메이션 완전 제외
    out = out[~out["장르"].isin(EXCLUDE_GENRES)].copy()

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

# =========================
# Strategy
# =========================
def _classify_strategy(offline_change, online_delta, x_thr, y_thr):
    if pd.isna(offline_change):
        return "기획 재검토"
    if offline_change > x_thr:
        return "극장 주력"
    if not pd.isna(online_delta) and online_delta >= y_thr:
        return "OTT 전환"
    return "기획 재검토"

def _market_memo(m_change: pd.DataFrame) -> str:
    if m_change is None or m_change.empty:
        return "요약 생성 불가"
    d = m_change.set_index("범주")
    if ("전체" in d.index) and ("국산" in d.index):
        a = d.loc["전체"]; k = d.loc["국산"]
        s_rel = "더 크다" if (k["매출액_증감률"] < a["매출액_증감률"]) else "더 작다"
        u_rel = "더 크다" if (k["관객수_증감률"] < a["관객수_증감률"]) else "더 작다"
        return (
            f"국산 매출 변화율은 {_safe_pct_text(k['매출액_증감률'])}로 전체 {_safe_pct_text(a['매출액_증감률'])} 대비 감소폭이 {s_rel}. "
            f"국산 관객 변화율은 {_safe_pct_text(k['관객수_증감률'])}로 전체 {_safe_pct_text(a['관객수_증감률'])} 대비 감소폭이 {u_rel}."
        )
    s = d.iloc[0]
    return f"{d.index[0]} 매출 {_safe_pct_text(s['매출액_증감률'])}, 관객 {_safe_pct_text(s['관객수_증감률'])}"

def _genre_memo(tmp: pd.DataFrame) -> str:
    if tmp is None or tmp.empty:
        return "요약 생성 불가"
    d = tmp.dropna(subset=["관객수_증감률"]).copy()
    if len(d) < 4:
        return "장르별 비교 요약 생성 불가"

    worst = d.nsmallest(2, "관객수_증감률")[["장르","관객수_증감률"]].values.tolist()
    best  = d.nlargest(2, "관객수_증감률")[["장르","관객수_증감률"]].values.tolist()

    w1, w2 = worst
    b1, b2 = best

    return (
        f"{w1[0]}와 {w2[0]}가 관객 변화율 {_safe_pct_text(w1[1])}, {_safe_pct_text(w2[1])}로 감소폭이 가장 크다. "
        f"반면 {b1[0]}와 {b2[0]}는 {_safe_pct_text(b1[1])}, {_safe_pct_text(b2[1])}로 감소폭이 상대적으로 제한적이다."
    )

def _online_memo(o_change: pd.DataFrame) -> str:
    if o_change is None or o_change.empty:
        return "요약 생성 불가"
    d = o_change.dropna(subset=["점유율_변화"]).copy()
    if len(d) < 4:
        return "온라인 요약 생성 불가"

    down = d.nsmallest(2, "점유율_변화")[["장르","점유율_변화"]].values.tolist()
    up   = d.nlargest(2, "점유율_변화")[["장르","점유율_변화"]].values.tolist()

    d1, d2 = down
    u1, u2 = up

    return (
        f"{d1[0]}와 {d2[0]}는 점유율 변화 {_safe_pp_text(d1[1])}, {_safe_pp_text(d2[1])}로 하락폭이 컸다. "
        f"{u1[0]}와 {u2[0]}는 {_safe_pp_text(u1[1])}, {_safe_pp_text(u2[1])}로 상승 폭이 상대적으로 컸다."
    )

# =========================
# Load data
# =========================
df_market, err = load_market()
if err:
    st.error(err); st.stop()

df_genre, err = load_genre()
if err:
    st.error(err); st.stop()

df_online, err = load_online()
if err:
    st.error(err); st.stop()

m_year, m_period, m_change = build_market_indicators(df_market)
g_agg, g_change = build_genre_indicators(df_genre)
o_period, o_change = build_online_indicators(df_online)

# =========================
# Strategy dataset
# =========================
base_scope = "국산" if "국산" in g_change["범주"].unique() else "전체"
base_label = "국산 영화 기준" if base_scope == "국산" else "전체 기준"

df_strategy = pd.DataFrame()
x_thr = None
y_thr = None

if (not o_change.empty) and (not g_change.empty):
    off = g_change[g_change["범주"]==base_scope][["장르","관객수_증감률","매출액_증감률"]].copy()
    merged = off.merge(o_change[["장르","점유율_변화"]], on="장르", how="left").dropna()

    if not merged.empty:
        x_thr = float(merged["관객수_증감률"].quantile(0.33))
        y_thr = float(merged["점유율_변화"].median())

        merged["추천_전략"] = merged.apply(
            lambda r: _classify_strategy(r["관객수_증감률"], r["점유율_변화"], x_thr, y_thr),
            axis=1
        )

        df_strategy = merged.rename(columns={
            "관객수_증감률": "오프라인_관객_변화율",
            "매출액_증감률": "오프라인_매출_변화율",
            "점유율_변화": "온라인_점유율_변화"
        }).copy()

# =========================
# Navigation
# =========================
st.sidebar.title("목차")
menu = st.sidebar.radio(
    "파트 선택",
    ["연구배경 및 필요성", "프로젝트 진행과정", "자료 해석", "프로젝트 성과", "프로젝트 기대효과"],
    index=0
)

# =========================
# Header
# =========================
st.title("티켓플레이션 시대, 국산 영화 생존 전략")
st.subheader("장르별 양극화 분석 및 최적 유통 경로 제언")
st.caption("코로나 전 2017–2019 | 코로나 후 2023–2025")

# =========================
# Pages
# =========================
if menu == "연구배경 및 필요성":
    st.title("💰 연구 배경 및 필요성")
    st.markdown("---")
    st.markdown("""
코로나19 이후 영화 티켓 가격이 10,000원에서 15,000원으로 약 50% 급등하면서, 영화 관람에 대한 소비자의 가격 탄력성이 극도로 높아졌습니다. 이는 국산 영화 시장 규모의 축소를 야기했으며, 장르별 흥행 격차가 극명하게 벌어지는 양극화현상의 핵심 동인이 되었습니다.

본 프로젝트는 코로나 전과 코로나 후를 비교하여 시장 지표의 변화 방향을 확인하고, 장르별로 타격이 집중되는 구간과 상대적으로 유지되는 구간을 구분하는 것을 목표로 합니다. 또한 온라인 점유율 변화를 함께 확인함으로써, 극장 주력과 OTT 전환이 필요한 장르를 구분할 수 있는 실증적 근거를 제시합니다.
""")

elif menu == "프로젝트 진행과정":
    st.markdown("## 프로젝트 진행과정")

    st.markdown("### 데이터 수집")
    st.markdown("""
- KOBIS 영화관입장권통합전산망에서 연도별 박스오피스 상위 영화 데이터를 수집하였다.                    
[KOBIS 연도별 박스오피스](https://www.kobis.or.kr/kobis/business/stat/boxs/findYearlyBoxOfficeList.do) 
- 전체와 국산을 구분하여 2017–2019, 2023–2025 연도별 지표를 구성하였다.  
- 장르별 분석을 위해 주요 9개 장르를 기준으로 별도 조회하여 흥행 데이터를 확보하였다.  
- VKOBIS 온라인상영관통합전산망에서 장르별 온라인 점유율 데이터를 수집하였다.                 
[VKOBIS 장르별 통계](https://www.vkobis.or.kr/statistics/selectGenreList.do)
""")

    st.markdown("### 수집 방식")
    st.markdown("""
- Selenium 기반 자동화를 통해 페이지 로딩 대기, 테이블 요소 탐색, 상위 N개 행 추출, CSV 저장 과정을 수행하였다.
""")

    st.info("아래 코드는 market_overview.csv 생성에 사용한 수집 코드 일부 발췌입니다.")
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

elif menu == "자료 해석":
    st.markdown("## 자료 해석")

    # 1) 시장 비교
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

        st.info(f"메모: {_market_memo(m_change)}")

    st.markdown("### 연도별 추세")
    _line(m_year.sort_values(["범주","연도"]), "연도", "관객수", "범주", "관객수 추세")
    _line(m_year.sort_values(["범주","연도"]), "연도", "매출액", "범주", "매출액 추세")

    st.divider()

    # 2) 장르별 타격 비교
    st.markdown("### 장르별 타격 비교")
    order = []
    if "전체" in g_change["범주"].unique():
        order.append("전체")
    if "국산" in g_change["범주"].unique():
        order.append("국산")
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
            use_container_width=True,
            height=420
        )

        _thin_barh(tmp, "관객수_증감률", "장르", f"{scope} 장르 관객 변화율")
        st.info(f"메모: {_genre_memo(tmp)}")

    st.divider()

    # 3) 온라인 점유율 비교
    st.markdown("### 장르별 온라인 타격 비교")
    if not o_change.empty:
        o_sorted = o_change.sort_values("점유율_변화")
        show = o_sorted.copy()
        show["점유율_전"] = show["점유율_전"].map(lambda v: f"{v*100:.2f}%")
        show["점유율_후"] = show["점유율_후"].map(lambda v: f"{v*100:.2f}%")
        show["점유율_변화"] = show["점유율_변화"].map(lambda v: f"{v*100:+.2f}%p")
        st.dataframe(
            show.rename(columns={"점유율_전":"점유율 코로나 전","점유율_후":"점유율 코로나 후","점유율_변화":"점유율 변화"}),
            use_container_width=True,
            height=420
        )

        tmp = o_sorted.copy()
        _thin_barh(tmp, "점유율_변화", "장르", "온라인 점유율 변화")
        st.info(f"메모: {_online_memo(o_change)}")

        if not df_strategy.empty and x_thr is not None and y_thr is not None:
            st.markdown("### 유통 전략 매트릭스")

            st.info(
                "기준선 설명: 세로 기준선은 오프라인 관객 변화율 하위 33% 지점이며, "
                "가로 기준선은 온라인 점유율 변화의 중앙값이다. "
                "오프라인 감소폭이 큰 장르 중 온라인 변화가 안정적이면 OTT 전환을 제안한다."
            )

            plot_df = df_strategy[["장르","오프라인_관객_변화율","온라인_점유율_변화","추천_전략"]].copy()

            color_map = {
                "극장 주력": "#2E7D32",
                "OTT 전환": "#C62828",
                "기획 재검토": "#616161"
            }

            fig = px.scatter(
                plot_df,
                x="오프라인_관객_변화율",
                y="온라인_점유율_변화",
                color="추천_전략",
                color_discrete_map=color_map,
                text="장르",
                hover_name="장르",
                template="plotly_white",
                title=f"{base_label} 오프라인 관객 변화율 × 온라인 점유율 변화"
            )

            fig.update_traces(textposition="top center", textfont_size=13)
            fig.update_layout(
                height=700,
                margin=dict(l=10, r=10, t=90, b=10),
                title_font_size=20,
                legend_title_text=""
            )
            fig.update_xaxes(tickformat=".0%", title="오프라인 관객 변화율")
            fig.update_yaxes(tickformat=".0%", title="온라인 점유율 변화")

            fig.add_vline(x=x_thr, line_width=2, line_dash="dash")
            fig.add_hline(y=y_thr, line_width=2, line_dash="dash")

            st.plotly_chart(fig, use_container_width=True)

            st.info(
                "💡 매트릭스 논리\n\n"
                "1. 🟢 극장 주력: 극장 경쟁력이 시장 평균보다 높습니다.\n\n"
                "2. 🔴 OTT 전환: 극장 타격은 크지만, 온라인 타격은 상대적으로 적거나 미미합니다.\n\n"
                "3. ⚪ 기획 재검토: 온/오프라인 모두에서 수요가 크게 약화되었습니다."
            )

            st.markdown("### 정리 표")
            out = df_strategy.copy()
            out["오프라인_관객_변화율"] = out["오프라인_관객_변화율"].apply(_fmt_pct)
            out["오프라인_매출_변화율"] = out["오프라인_매출_변화율"].apply(_fmt_pct)
            out["온라인_점유율_변화"] = out["온라인_점유율_변화"].apply(_fmt_pp)
            out = out.rename(columns={
                "오프라인_관객_변화율": "오프라인 관객 변화율",
                "오프라인_매출_변화율": "오프라인 매출 변화율",
                "온라인_점유율_변화": "온라인 점유율 변화",
                "추천_전략": "전략 제언"
            })[["장르","오프라인 관객 변화율","오프라인 매출 변화율","온라인 점유율 변화","전략 제언"]]
            order_map = {"극장 주력": 0, "OTT 전환": 1, "기획 재검토": 2}
            out["_o"] = out["전략 제언"].map(order_map).fillna(9)
            out = out.sort_values(["_o","장르"]).drop(columns=["_o"])
            st.dataframe(out, use_container_width=True, height=520)
    else:
        st.warning("online_stats.csv에서 점유율 데이터를 충분히 읽지 못했습니다.")

elif menu == "프로젝트 성과":
    st.markdown("## 프로젝트 성과")
    st.markdown("""
본 프로젝트는 티켓 가격 급등 이후 영화 산업의 수요 축소가 시장 지표에서 확인되는지를 코로나 전후 비교로 검증하였다. 전체 시장과 국산 영화 시장을 분리하여 관객과 매출 변화율을 함께 제시함으로써, 가격 상승 효과가 포함된 매출 지표를 수요 변화와 결합해 판단할 수 있도록 구성하였다.  

장르별 변화율 분석을 통해 타격이 집중되는 장르와 상대적으로 유지되는 장르를 분류할 수 있는 근거를 구성하였다. 또한 온라인 점유율 변화를 결합하여 장르별로 극장 주력, OTT 전환, 기획 재검토로 연결되는 전략적 분류 구조를 완성하였다.
""")

    if not df_strategy.empty:
        out = df_strategy.copy()
        out["오프라인_관객_변화율"] = out["오프라인_관객_변화율"].apply(_fmt_pct)
        out["오프라인_매출_변화율"] = out["오프라인_매출_변화율"].apply(_fmt_pct)
        out["온라인_점유율_변화"] = out["온라인_점유율_변화"].apply(_fmt_pp)
        out = out.rename(columns={
            "오프라인_관객_변화율": "오프라인 관객 변화율",
            "오프라인_매출_변화율": "오프라인 매출 변화율",
            "온라인_점유율_변화": "온라인 점유율 변화",
            "추천_전략": "전략 제언"
        })[["장르","오프라인 관객 변화율","오프라인 매출 변화율","온라인 점유율 변화","전략 제언"]]
        st.dataframe(out, use_container_width=True, height=520)

elif menu == "프로젝트 기대효과":
    st.title("🎬 최종 제언 및 기대 효과")
    st.markdown("---")

    st.subheader("배급 전략 시뮬레이터")  # <- AI 제거
    st.write("분석 결과를 기반으로, 기획 중인 국산 영화의 권장 유통 전략을 확인할 수 있습니다.")

    if df_strategy.empty:
        st.warning("전략 시뮬레이터를 구성하기 위한 결합 데이터가 부족합니다.")
    else:
        genre_list = sorted(df_strategy["장르"].unique().tolist())
        selected_genre = st.selectbox("기획 중인 영화의 장르를 선택하세요:", genre_list)

        row = df_strategy[df_strategy["장르"] == selected_genre].iloc[0]
        strategy = row["추천_전략"]

        st.divider()

        c1, c2, c3 = st.columns(3)
        c1.metric("오프라인 관객 변화율", _fmt_pct(row["오프라인_관객_변화율"]))
        c2.metric("온라인 점유율 변화", _fmt_pp(row["온라인_점유율_변화"]))
        c3.metric("전략 제언", strategy)

        st.divider()

        if strategy == "극장 주력":
            st.success(
                f"✅ 극장 주력\n\n"
                f"- '{selected_genre}' 장르는 오프라인 감소폭이 기준선보다 작아 극장 수요가 상대적으로 유지되는 구간에 위치한다.\n"
                f"- 특수관, 체험형 포맷, 이벤트 상영 등으로 극장 경쟁력을 강화하는 전략이 유효하다.\n"
                f"- 기대효과: 극장 주력 장르 중심의 수익 회복 가능성을 높이고, 극장 유입 동력을 유지하는 포트폴리오 설계가 가능하다."
            )
        elif strategy == "OTT 전환":
            st.warning(
                f"📺 OTT 전환\n\n"
                f"- '{selected_genre}' 장르는 오프라인 타격이 큰 구간이지만 온라인 점유율 변화가 상대적으로 안정적이다.\n"
                f"- OTT 공개 또는 단기 홀드백 전략을 통해 손익 변동성을 낮출 수 있다.\n"
                f"- 기대효과: 극장 P&A 비용 부담을 줄이고, 플랫폼 기반 수익 모델로 리스크를 완화할 수 있다."
            )
        else:
            st.error(
                f"⚠️ 기획 재검토\n\n"
                f"- '{selected_genre}' 장르는 오프라인 감소폭이 크고 온라인에서도 뚜렷한 방어 신호가 약한 구간에 위치한다.\n"
                f"- 제작비 구조 조정, 타겟 축소, 니치 전략 등 기획 단계 재설계가 필요하다.\n"
                f"- 기대효과: 불필요한 대규모 마케팅 지출을 줄이고, 자원 배분 효율을 높여 실패 비용을 최소화할 수 있다."
            )

    st.subheader("기대효과 요약")
    st.markdown("""
- 장르별 타격 정도를 근거로 개봉 채널 선택을 분리할 수 있어, 제작·배급 단계의 의사결정 불확실성을 낮출 수 있다.  
- 극장 타격이 큰 장르는 OTT 공개를 통해 리스크를 낮추고, 타격이 적은 장르는 극장 개봉을 강화하여 수익 회복 가능성을 높일 수 있다.  
- 국산 영화의 취약 구간이 장르 단위로 확인될 경우, 국산 영화 시장의 포트폴리오 구성과 배급 전략을 장르 중심으로 재정비하는 근거로 활용 가능하다.
""")
