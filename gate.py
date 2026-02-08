import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

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
    
    # 게이트 입력 (기본값을 빈칸으로 두었습니다)
    st.subheader("담당 게이트")
    gate_input = st.text_input("번호 입력 (비워두면 전체 조회)", value="", placeholder="예: 10, 105 (비워두면 다 보입니다)")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 가져오기 (핵심 로직)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    # 1. 키 보정
    real_key = unquote(key_input)
    
    # 2. 게이트 번호 정리 (입력값이 없으면 빈 리스트가 됨)
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
                        # [수정됨] 게이트 칸이 비어있거나(전체조회), 번호가 맞으면 추가
                        if not target_gates or str(item.get('gate')) in target_gates:
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
                        # [수정됨] 게이트 칸이 비어있거나(전체조회), 번호가 맞으면 추가
                        if not target_gates or str(item.get('gate')) in target_gates:
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
        st.info("데이터가 없습니다.")
        st.write("- 아직 키 승인이 안 되었거나(1시간 소요)")
        st.write("- 해당 시간대에 운항 스케줄이 없을 수 있습니다.")
        
        # 확인용 링크
        real_key = unquote(api_key_input)
        test_url = f"http://apis.data.go.kr/B551177/StatusOfFlights/getFltDeparturesDeOdp?serviceKey={real_key}&type=json&terminalId=P01&numOfRows=5&pageNo=1"
        st.markdown(f"[👉 클릭해서 데이터 확인하기]({test_url})")
        
    else:
        # 시간순 정렬
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        # 타이틀 (필터링 여부 표시)
        if not gate_input.strip():
            st.success(f"🔍 전체 조회 모드: 총 {len(df)}건")
        else:
            st.success(f"🔍 게이트 {gate_input} 조회: 총 {len(df)}건")

        for index, row in df.iterrows():
            # 데이터 추출
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            # 시간 포맷
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str
