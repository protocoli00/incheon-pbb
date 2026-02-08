import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 항공기 운항", page_icon="✈️", layout="centered")
st.title("✈️ PBB 항공기 운항 현황")
st.caption("공공데이터포털 [항공기 운항편 조회] 전용")

# ==========================================
# 2. 사이드바 (설정)
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정 메뉴")
    
    # API 키 입력
    api_key_input = st.text_input("인증키 입력 (Decoding 권장)", type="password")
    
    # 터미널 선택
    st.subheader("터미널 선택")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역 선택", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    # 게이트 입력 (기본값을 빈칸으로 둠 -> 전체 조회)
    st.subheader("담당 게이트")
    gate_input = st.text_input("번호 입력 (비워두면 전체 조회)", value="", placeholder="예: 10, 105 (비워두면 다 보입니다)")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 가져오기
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    # 1. 키 보정
    real_key = unquote(key_input)
    
    # 2. 게이트 번호 정리 (입력값이 없으면 빈 리스트)
    target_gates = []
    if gate_input_str.strip():
        target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    
    # 3. API 주소 설정
    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp" # 출발
    url_arr = f"{base_url}/getFltArrivalsDeOdp"   # 도착
    
    all_flights = []

    # 4. 터미널별 조회
    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 파라미터 (100개 요청)
        params = {
            "serviceKey": real_key,
            "type": "json",
            "terminalId": t_code,
            "numOfRows": "100", 
            "pageNo": "1"
        }

        # [출발 데이터]
        try:
            res = requests.get(url_dep, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        # 게이트가 비어있거나(전체), 번호가 일치하면 추가
                        current_gate = str(item.get('gate', ''))
                        if not target_gates or current_gate in target_gates:
                            item['type'] = '출발'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

        # [도착 데이터]
        try:
            res = requests.get(url_arr, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        # 게이트가 비어있거나(전체), 번호가 일치하면 추가
                        current_gate = str(item.get('gate', ''))
                        if not target_gates or current_gate in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 API 키를 넣어주세요.")
else:
    with st.spinner('데이터 조회 중...'):
        df = get_flight_data(api_key_input, gate_input, selected_terminals)

    if df.empty:
        st.info("데이터가 없습니다.")
        st.write("- 키 승인 대기중 (1시간 소요)")
        st.write("- 해당 시간대에 운항 스케줄 없음")
        
        # 확인용 링크
        real_key = unquote(api_key_input)
        test_url = f"http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp?serviceKey={real_key}&type=json&terminalId=P01&numOfRows=5&pageNo=1"
        st.markdown(f"[👉 클릭해서 데이터 확인하기]({test_url})")
        
    else:
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        # 타이틀
        count = len(df)
        if not gate_input.strip():
            st.success(f"🔍 전체 조회 모드: 총 {count}건")
        else:
            st.success(f"🔍 게이트 {gate_input} 조회: 총 {count}건")

        for index, row in df.iterrows():
            # 데이터 추출 (에러 방지용 안전한 코드)
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            # 시간 포맷 (안전하게 분리)
            t_str = str(row.get('scheduleDateTime', ''))
            if len(t_str) >= 12:
                # YYYYMMDDHHMM -> HH:MM
                hour = t_str[8:10]
                minute = t_str[10:12]
                f_time = f"{hour}:{minute}"
            else:
                f_time = "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            airport = row.get('airport', '-') 
            
            # 색상 설정
            bg_color = "#ffffff"
            border_color = "#ddd"
            icon = "✈️"
            route_str = ""

            if row_type == '도착':
                bg_color = "#e7f5ff" # 파랑
                border_color = "#004085"
                icon = "🛬 IN"
                route_str = f"출발: {airport}"
            else:
                route_str = f"목적: {airport}"
                if "탑승" in remark:
                    bg_color = "#d4edda" # 초록
                    border_color = "#155724"
                    icon = "🟢 OUT"
                elif "마감" in remark:
                    bg_color = "#f8d7da" # 빨강
                    border_color = "#721c24"
                    icon = "🔴 OUT"
                elif "지연" in remark:
                    bg_color = "#fff3cd" # 노랑
                    border_color = "#856404"
                    icon = "🟡 OUT"
                else:
                    icon = "🛫 OUT"

            # HTML 생성 (문자열 끊김 방지)
            html = f"""
            <div style="padding: 15px; margin-bottom: 12px; border-radius: 12px; background-color: {bg_color}; border: 1px solid {border_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 24px; font-weight: bold; color: #333;">{f_time}</span>
                    <span style="font-size: 18px; font-weight: bold; color: #333;">{remark}</span>
                </div>
                <div style="font-size: 20px; font-weight: bold; margin-bottom: 5px;">
                    <span style="background-color: #333; color: #fff; padding: 2px 8px; border-radius: 5px; font-size: 16px; margin-right: 5px;">G{gate}</span>
                    {flight_no}
                </div>
                <div style="font-size: 15px; color: #555;">
                    <b>{icon}</b> | {airline} <br>
                    {route_str}
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
