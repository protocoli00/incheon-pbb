import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 현황판", page_icon="🛫", layout="centered")
st.title("🛫 PBB 현황판 (T1)")
st.caption("체크인 카운터 자동 변환 (예: H05→H1, H20→H2)")

# ==========================================
# 2. 사이드바 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    # API 키 입력
    api_key_input = st.text_input("인증키 입력 (Decoding)", type="password")
    
    # 터미널 (T1 기본 선택)
    st.subheader("터미널")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=['T1'])
    
    # 게이트 (비워두면 전체)
    st.subheader("게이트")
    gate_input = st.text_input("번호 (비워두면 전체)", value="")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 카운터 변환 함수 (핵심 기능)
# ==========================================
def format_counter(text):
    """
    데이터가 'H05-H18' 등으로 들어오면
    앞자리 숫자가 1~18이면 -> H1 카운터
    19 이상이면 -> H2 카운터로 변환하여 표시
    """
    if not text or text == "-" or text == "None":
        return "-"
    
    try:
        # 'H05-H18' 에서 앞부분 'H05'만 추출
        start_code = text.split('-')[0].strip()
        
        # 알파벳 (예: H)
        alpha = start_code[0]
        # 숫자 (예: 05) -> 정수형 5
        number = int(start_code[1:])
        
        # 1~18번은 1구역, 그 외(19~)는 2구역
        suffix = "1" if number <= 18 else "2"
        
        return f"{alpha}{suffix} 카운터"
    except:
        # 변환 실패 시(형식이 다를 때) 원래 데이터 그대로 표시
        return text

# ==========================================
# 4. 데이터 가져오기 로직
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    real_key = unquote(key_input)
    today_str = datetime.now().strftime("%Y%m%d") # 오늘 날짜 자동 입력
    
    # 게이트 필터 정리
    target_gates = []
    if gate_input_str.strip():
        target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]

    # API 주소
    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp"
    url_arr = f"{base_url}/getFltArrivalsDeOdp"
    
    all_flights = []

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        params = {
            "serviceKey": real_key, "type": "json",
            "terminalId": t_code, "searchDate": today_str,
            "numOfRows": "300", "pageNo": "1"
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
                        current_gate = str(item.get('gate', ''))
                        if not target_gates or current_gate in target_gates:
                            item['type'] = '출발'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

        # --- [2] 도착 데이터 ---
        try:
            res = requests.get(url_arr, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        current_gate = str(item.get('gate', ''))
                        if not target_gates or current_gate in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 5. 화면 출력 (색상 강조 디자인)
# ==========================================
if not api_key_input:
    st.warning("👈 왼쪽 사이드바에 인증키를 입력해주세요.")
else:
    with st.spinner('실시간 데이터를 불러오는 중...'):
        df = get_flight_data(api_key_input, gate_input, selected_terminals)

    if df.empty:
        st.info("조건에 맞는 운항 스케줄이 없습니다.")
    else:
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        count = len(df)
        st.success(f"총 {count}건 조회됨")

        for index, row in df.iterrows():
            # 기본 정보 추출
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            # 시간 포맷 (HH:MM)
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str[8:10]}:{t_str[10:12]}" if len(t_str) >= 12 else "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            
            # --- 🎨 하단 정보 및 색상 로직 ---
            bg_color = "#ffffff"
            text_color = "#333"
            bottom_info = "" # 카운터 또는 수하물 정보

            if row_type == '도착':
                bg_color = "#cce5ff" # 파랑 (도착)
                carousel = str(row.get('carousel', '-'))
                bottom_info = f"수하물 수취대: {carousel}"
                status_text = "도착"
            else:
                # 출발일 때 카운터 변환 함수 적용
                raw_counter = row.get('chkinRange', '-')
                conv_counter = format_counter(raw_counter)
                
                bottom_info = f"Check-in: {conv_counter}"
                status_text = remark

                # 상태별 배경색 지정
                if "탑승" in remark: bg_color = "#d4edda" # 초록
                elif "마감" in remark or "Final" in remark: bg_color = "#f8d7da" # 빨강
                elif "지연" in remark: bg_color = "#fff3cd" # 노랑
                elif "결항" in remark: bg_color = "#e2e3e5" # 회색

            # HTML 카드 출력
            st.markdown(f"""
            <div style="
                background-color: {bg_color};
                padding: 16px;
                margin-bottom: 12px;
                border-radius: 12px;
                border: 1px solid #ddd;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 26px; font-weight: 800; color: #333;">{f_time}</span>
                    <span style="font-size: 18px; font-weight: bold; color: #444;">{status_text}</span>
                </div>
                
                <div style="font-size: 22px; font-weight: bold; margin-bottom: 6px; color: #000;">
                    <span style="background-color: #333; color: #fff; padding: 2px 8px; border-radius: 6px; margin-right: 6px; font-size: 18px;">G{gate}</span>
                    {flight_no}
                </div>
                
                <div style="font-size: 16px; color: #555; margin-bottom: 10px;">
                    {airline}
                </div>
                
                <div style="
                    border-top: 2px dotted #aaa; 
                    padding-top: 8px; 
                    font-size: 18px; 
                    font-weight: bold; 
                    color: #222; 
                    text-align: right;
                ">
                    {bottom_info}
                </div>
            </div>
            """, unsafe_allow_html=True)
