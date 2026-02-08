import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime
import pytz # 한국 시간 계산용

# ==========================================
# 1. 화면 설정 및 시계
# ==========================================
st.set_page_config(page_title="인천공항 현황", page_icon="🛫", layout="centered")

# 한국 시간(KST) 구하기
KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)
time_str = now_kst.strftime("%H:%M:%S")
date_str = now_kst.strftime("%Y년 %m월 %d일")

# 👇 요청하신 제목 적용!
st.title("🛫 인천공항 카운터 및 탑승교 정보")

# 상단 시계 디자인 (새로고침 기준 스냅샷)
st.markdown(f"""
<div style="
    text-align: center; 
    background-color: #f0f2f6; 
    padding: 15px; 
    border-radius: 10px; 
    margin-bottom: 20px; 
    border: 2px solid #dfe2e5;">
    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">📅 데이터 조회 기준 시간 ({date_str})</div>
    <div style="font-size: 32px; font-weight: bold; color: #333; font-family: sans-serif; letter-spacing: 1px;">
        {time_str}
    </div>
    <div style="font-size: 12px; color: #888; margin-top: 5px;">
        (새로고침 버튼을 눌러야 갱신됩니다)
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    api_key_input = st.text_input("인증키 입력", type="password")
    
    # 500 에러 해결사
    use_encoding = st.checkbox("데이터 안 나오면 체크(키 변환)", value=False)
    
    st.subheader("터미널")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=['T1'])
    
    # 👇 [수정됨] 입력 메뉴 이름 변경 및 설명
    st.subheader("검색 필터")
    gate_input = st.text_input(
        "카운터 & 탑승Gate (쉼표 구분)", 
        value="", 
        placeholder="예: M1, 112 (비워두면 전체)"
    )
    st.caption("💡 팁: 'M1'은 카운터로, '112'는 게이트로 자동 인식합니다.")
    
    if st.button("새로고침 (시간갱신)"):
        st.rerun()

# ==========================================
# 3. 카운터 변환 함수 (핵심 로직)
# ==========================================
def get_short_counter(text):
    """
    데이터(H01-H18)를 받아서 짧은 이름(H1)으로 변환해주는 함수
    (검색 매칭용)
    """
    if not text or text == "-" or text == "None": return None
    try:
        start_code = text.split('-')[0].strip() # H05 추출
        alpha = start_code[0] # H
        number = int(start_code[1:]) # 5
        suffix = "1" if number <= 18 else "2"
        return f"{alpha}{suffix}" # H1 반환
    except:
        return None

def format_counter_display(text):
    """
    화면에 보여줄 때: H1 -> 'H1 카운터' 라고 붙여줌
    """
    short = get_short_counter(text)
    if short:
        return f"{short} 카운터"
    return text if text else "-"

# ==========================================
# 4. 데이터 로직 (하이브리드 검색 적용)
# ==========================================
def get_flight_data(key_input, search_input_str, terminals_to_check, use_enc):
    if not key_input: return pd.DataFrame(), None

    real_key = key_input if use_enc else unquote(key_input)
    today_str = datetime.now(KST).strftime("%Y%m%d")
    
    # 검색어 정리 (대문자로 통일)
    # 예: "m1, 112" -> ['M1', '112']
    search_targets = []
    if search_input_str.strip():
        search_targets = [x.strip().upper() for x in search_input_str.split(',') if x.strip()]

    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp"
    url_arr = f"{base_url}/getFltArrivalsDeOdp"
    
    all_flights = []
    error_msg = None

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 카운터 검색을 위해 데이터를 넉넉히 가져옴 (200개)
        params = {
            "serviceKey": real_key, "type": "json",
            "terminalId": t_code, "searchDate": today_str,
            "numOfRows": "200", 
            "pageNo": "1"
        }

        # --- [1] 출발 데이터 ---
        try:
            res = requests.get(url_dep, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        # 데이터 추출
                        gate_num = str(item.get('gate', '')).strip().upper()
                        raw_counter = str(item.get('chkinRange', ''))
                        short_counter = get_short_counter(raw_counter) # 예: H1
                        
                        # 👇 [핵심] 하이브리드 필터링 로직
                        # 1. 검색어가 없으면 -> 무조건 통과 (전체조회)
                        # 2. 게이트 번호(112)가 검색어에 있으면 -> 통과
                        # 3. 카운터 이름(H1)이 검색어에 있으면 -> 통과
                        is_match = False
                        if not search_targets:
                            is_match = True
                        else:
                            if gate_num in search_targets: is_match = True
                            if short_counter and short_counter in search_targets: is_match = True
                        
                        if is_match:
                            item['type'] = '출발'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
            else:
                error_msg = f"서버 상태코드: {res.status_code}"
        except Exception as e:
            error_msg = f"통신 오류: {e}"

        # --- [2] 도착 데이터 ---
        try:
            res = requests.get(url_arr, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        gate_num = str(item.get('gate', '')).strip().upper()
                        
                        # 도착은 카운터 정보가 없으므로 게이트 매칭만 수행
                        is_match = False
                        if not search_targets:
                            is_match = True
                        else:
                            if gate_num in search_targets: is_match = True
                            
                        if is_match:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights), error_msg

# ==========================================
# 5. 화면 출력 (여기에 색상 로직이 있습니다!)
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 인증키를 입력해주세요.")
else:
    with st.spinner('데이터 조회 및 필터링 중...'):
        df, err = get_flight_data(api_key_input, gate_input, selected_terminals, use_encoding)

    if err and df.empty:
        st.error(f"조회 실패 ({err})")
        st.info("사이드바의 '데이터 안 나오면 체크' 박스를 눌러보세요.")
    
    elif df.empty:
        st.info("검색 조건에 맞는 운항 정보가 없습니다.")
    else:
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        st.success(f"조회 성공: {len(df)}건")

        for index, row in df.iterrows():
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str[8:10]}:{t_str[10:12]}" if len(t_str) >= 12 else "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            
            # 카운터 변환 (화면 표시용)
            raw_counter = row.get('chkinRange', '-')
            display_counter = format_counter_display(raw_counter)
            
            # === 🎨 디자인/색상 결정 로직 ===
            bg_color = "#ffffff" # 기본 흰색
            bottom_info = ""

            if row_type == '도착':
                bg_color = "#cce5ff" # 🟦 파란색 (도착)
                status_text = "도착"
                bottom_info = f"수하물 수취대: {str(row.get('carousel', '-'))}"
            else:
                status_text = remark
                bottom_info = f"Check-in: {display_counter}"
                
                # 상태별 색상 변경
                if "탑승" in remark: bg_color = "#d4edda"      # 🟩 초록색 (탑승중)
                elif "마감" in remark: bg_color = "#f8d7da"    # 🟥 빨간색 (마감)
                elif "지연" in remark: bg_color = "#fff3cd"    # 🟨 노란색 (지연)
                elif "결항" in remark: bg_color = "#e2e3e5"    # ⬜ 회색 (결항)

            # HTML 카드 출력
            st.markdown(f"""
            <div style="background-color:{bg_color}; padding:15px; margin-bottom:10px; border-radius:12px; border:1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span style="font-size:24px; font-weight:800; color:#333;">{f_time}</span>
                    <span style="font-size:18px; font-weight:bold; color:#444;">{status_text}</span>
                </div>
                <div style="font-size:22px; font-weight:bold; margin-bottom:5px;">
                    <span style="background:#333; color:white; padding:2px 8px; border-radius:5px; margin-right:5px;">G{gate}</span>
                    {flight_no}
                </div>
                <div style="font-size:16px; color:#555; margin-bottom:8px;">
                    {airline}
                </div>
                <div style="border-top:2px dotted #aaa; padding-top:8px; text-align:right; font-weight:bold; font-size:18px;">
                    {bottom_info}
                </div>
            </div>
            """, unsafe_allow_html=True)
