import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote

# ==========================================
# 1. 화면 설정
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
    
    # 게이트 입력
    st.subheader("담당 게이트")
    gate_input = st.text_input("번호 입력 (쉼표로 구분)", value="10, 105, 230")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 가져오기 (핵심 로직)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    # 1. 키 보정 (Encoding키가 들어와도 Decoding으로 변환)
    real_key = unquote(key_input)
    
    # 2. 게이트 번호 정리
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    
    # 3. API 주소 설정 (선생님이 주신 그 주소!)
    base_url = "http://apis.data.go.kr/B551177/StatusOfFlights"
    url_dep = f"{base_url}/getFltDeparturesDeOdp" # 출발
    url_arr = f"{base_url}/getFltArrivalsDeOdp"   # 도착
    
    all_flights = []

    # 4. 터미널별 조회 (T1 -> 탑승동 -> T2)
    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 요청 파라미터 (항공기 운항편 스펙 준수)
        params = {
            "serviceKey": real_key,
            "type": "json",       # JSON 형식
            "terminalId": t_code, # 터미널 ID (P01 등)
            "numOfRows": "100",   # 넉넉하게 100개
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
                        # 게이트 매칭
                        if str(item.get('gate')) in target_gates:
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
                        # 게이트 매칭
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력 (디자인)
# ==========================================
if not api_key_input:
    st.warning("👈 사이드바에 API 키를 넣어주세요.")
else:
    with st.spinner('데이터 조회 중...'):
        df = get_flight_data(api_key_input, gate_input, selected_terminals)

    if df.empty:
        st.error("데이터가 없습니다.")
        st.info("💡 해결 방법")
        st.write("1. 게이트 번호에 현재 비행기가 없는 경우일 수 있습니다.")
        st.write("2. API 키가 아직 승인 대기 중일 수 있습니다 (1시간 소요).")
        
        # 직접 확인용 링크 (가장 확실한 방법)
        real_key = unquote(api_key_input)
        test_url = f"http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp?serviceKey={real_key}&type=json&terminalId=P01&numOfRows=5&pageNo=1"
        st.markdown(f"[👉 클릭해서 데이터가 뜨는지 확인하기 (테스트 링크)]({test_url})")
        
    else:
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        st.success(f"총 {len(df)}건의 운항 정보를 찾았습니다.")

        for index, row in df.iterrows():
            # 데이터 추출
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정') # 현황 정보
            if not remark: remark = "예정"
            
            # 시간 포맷 (YYYYMMDDHHMM -> HH:MM)
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str[8:10]}:{t_str[10:12]}" if len(t_str) >= 12 else "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            airport = row.get('airport', '-') # 출발/도착 공항명
            
            # 색상 및 아이콘 결정
            if row_type == '도착':
                bg_color = "#e7f5ff" # 파랑 (도착)
                border_color = "#004085"
                icon = "🛬 IN"
                route_str = f"출발: {airport}"
            else:
                # 출발 상태별 색상
                if "탑승" in remark:
                    bg_color = "#d4edda" # 초록 (탑승중) - 가장 중요!
                    border_color = "#155724"
                    icon = "🟢 OUT"
                elif "마감" in remark:
                    bg_color = "#f8d7da" # 빨강 (마감)
                    border_color = "#721c24"
                    icon = "🔴 OUT"
                elif "지연" in remark:
                    bg_color = "#fff3cd" # 노랑
                    border_color = "#856404"
                    icon = "🟡 OUT"
                else:
                    bg_color = "#ffffff" # 흰색 (대기)
                    border_color = "#ddd"
                    icon = "🛫 OUT"
                route_str = f"목적: {airport}"

            # 카드 HTML 출력
            st.markdown(f"""
            <div style="
                padding: 15px; 
                margin-bottom: 12px; 
                border-radius: 12px; 
                background-color: {bg_color}; 
                border: 1px solid {border_color};
                box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                
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
            """, unsafe_allow_html=True)
