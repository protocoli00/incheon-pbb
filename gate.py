import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ==========================================
# 1. 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 멀티뷰", page_icon="🛫")
st.title("🛫 PBB 멀티 게이트 현황")

# ==========================================
# 2. 사이드바 (입력창 수정됨)
# ==========================================
with st.sidebar:
    st.header("설정 메뉴")
    api_key = st.text_input("API 인증키", type="password")
    
    st.subheader("터미널 선택")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("터미널 선택", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    st.subheader("담당 게이트 (여러 개 가능)")
    # 쉼표로 구분해서 입력하도록 안내
    gate_input = st.text_input("번호 입력 (쉼표로 구분)", value="10, 11, 12", help="예: 7, 8, 9 또는 105, 106")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 로직 (여러 게이트 처리)
# ==========================================
def get_flight_data(key, gate_input_str, terminals_to_check):
    url_dep = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerDeparturesOdp"
    url_arr = "http://apis.data.go.kr/B551177/StatusOfPassengerFlightsOdp/getPassengerArrivalsOdp"
    
    # 입력된 문자열("10, 11")을 리스트(["10", "11"])로 변환 및 공백 제거
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    
    all_flights = []

    for terminal_name in terminals_to_check:
        t_code = terminal_options[terminal_name]
        
        # [출발] 조회
        try:
            params = {"serviceKey": key, "type": "json", "terminalId": t_code, "numOfRows": "300", "pageNo": "1"}
            items = requests.get(url_dep, params=params).json()['response']['body']['items']
            if not isinstance(items, list): items = [items]
            
            for item in items:
                # 리스트에 있는 게이트 번호 중 하나라도 맞으면 추가
                if str(item.get('gate')) in target_gates:
                    item['type'] = '출발'
                    item['terminal_name'] = terminal_name
                    all_flights.append(item)
        except: pass

        # [도착] 조회
        try:
            params = {"serviceKey": key, "type": "json", "terminalId": t_code, "numOfRows": "300", "pageNo": "1"}
            items = requests.get(url_arr, params=params).json()['response']['body']['items']
            if not isinstance(items, list): items = [items]
            
            for item in items:
                # 리스트에 있는 게이트 번호 중 하나라도 맞으면 추가
                if str(item.get('gate')) in target_gates:
                    item['type'] = '도착'
                    item['terminal_name'] = terminal_name
                    all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 색상/이모지 설정
# ==========================================
def get_status_info(row_type, status):
    status = str(status)
    if row_type == '도착':
        if "도착" in status or "착륙" in status: return "🔵", "#e7f5ff"
        else: return "⚪", "#f8f9fa"
    else:
        if "탑승중" in status: return "🟢", "#e6fffa" # 초록
        elif "마감" in status or "Final" in status: return "🔴", "#fff5f5" # 빨강
        elif "지연" in status: return "🟡", "#fff9db" # 노랑
        elif "출발" in status: return "🔵", "#e7f5ff" # 파랑
        else: return "⚪", "#f8f9fa"

# ==========================================
# 5. 화면 출력
# ==========================================
if not api_key:
    st.warning("API 키를 입력해주세요.")
else:
    # 카드 스타일
    st.markdown("""
    <style>
    .flight-card { padding: 15px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #ddd; }
    .time-text { font-size: 24px; font-weight: bold; color: #333; }
    .status-text { font-size: 18px; font-weight: bold; float: right; }
    .gate-badge { background-color: #333; color: white; padding: 2px 8px; border-radius: 4px; font-size: 14px; font-weight: bold; margin-right: 5px;}
    </style>
    """, unsafe_allow_html=True)

    with st.spinner('전체 게이트 통합 조회 중...'):
        df_result = get_flight_data(api_key, gate_input, selected_terminals)

    if df_result.empty:
        st.info("해당 게이트들에 예정된 스케줄이 없습니다.")
    else:
        # 시간순으로 정렬 (게이트 번호 상관없이 급한 순서대로)
        df_result = df_result.sort_values(by='scheduleDateTime')

        for index, row in df_result.iterrows():
            row_type = row['type']
            current_gate = row.get('gate', '?') # 현재 이 비행기의 게이트
            time_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
            remark = row.get('remark', '') 
            flight_no = row.get('flightId', '')
            airline = row.get('airline', '')
            airport = row.get('airport', '')

            emoji, bg_color = get_status_info(row_type, remark)
            tag = "🛬 IN" if row_type == '도착' else "🛫 OUT"
            
            # 화면 출력 (게이트 번호를 강조해서 보여줌)
            st.markdown(f"""
            <div class="flight-card" style="background-color: {bg_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="time-text">{f_time}</span>
                    <span class="status-text">{emoji} {remark}</span>
                </div>
                <div style="margin: 5px 0;">
                    <span class="gate-badge">G{current_gate}</span> 
                    <span style="font-size: 18px; font-weight: bold;">{flight_no}</span>
                </div>
                <div style="font-size: 14px; color: #666;">
                    <b>{tag}</b> | {airline} ({airport})
                </div>
            </div>
            """, unsafe_allow_html=True)
