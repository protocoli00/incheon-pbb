import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="PBB 통합 현황판", page_icon="🛫", layout="centered")
st.title("🛫 PBB 통합 스케줄 (전체운항)")
st.caption("출발(Out) + 도착(In) 통합 조회 / 자동 키 보정 적용됨")

# ==========================================
# 2. 사이드바 (설정 메뉴)
# ==========================================
with st.sidebar:
    st.header("설정 메뉴")
    
    # 1. API 키 입력
    api_key_input = st.text_input("인증키를 입력하세요", type="password")
    
    # 2. 터미널 선택
    st.subheader("터미널 선택")
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("조회할 구역", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    # 3. 게이트 선택
    st.subheader("게이트 번호")
    gate_input = st.text_input("번호 입력 (쉼표로 구분)", value="10, 105, 230")
    
    if st.button("새로고침"):
        st.rerun()

# ==========================================
# 3. 데이터 조회 함수 (출발 + 도착)
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame()

    # 키 자동 보정 (Encoding/Decoding 문제 해결)
    real_key = unquote(key_input)
    
    # 게이트 번호 정리 (공백 제거)
    target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]
    all_flights = []

    # API 주소 (전체 운항 현황 - 출발/도착)
    url_dep = "http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp"
    url_arr = "http://apis.data.go.kr/B551177/statusOfAllFltArOdp/getStatusOfAllFltArOdp"

    # 선택된 터미널 반복 조회
    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 공통 파라미터
        params = {
            "serviceKey": real_key,
            "type": "json",
            "searchTerminalId": t_code, # 전체운항 API용 파라미터
            "numOfRows": "100",
            "pageNo": "1"
        }

        # --- [1] 출발(Departure) 데이터 조회 ---
        try:
            res = requests.get(url_dep, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '출발'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass # 에러나면 무시하고 계속 진행

        # --- [2] 도착(Arrival) 데이터 조회 ---
        try:
            res = requests.get(url_arr, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('response', {}).get('body', {}).get('items')
                if items:
                    if not isinstance(items, list): items = [items]
                    for item in items:
                        if str(item.get('gate')) in target_gates:
                            item['type'] = '도착'
                            item['terminal_name'] = t_name
                            all_flights.append(item)
        except: pass 

    return pd.DataFrame(all_flights) if all_flights else pd.DataFrame()

# ==========================================
# 4. 화면 출력 (카드 디자인)
# ==========================================
if not api_key_input:
    st.warning("👈 왼쪽 사이드바에 인증키를 입력해주세요.")
elif not selected_terminals:
    st.warning("최소 한 개 이상의 터미널을 선택해주세요.")
else:
    # 로딩 표시
    with st.spinner('실시간 데이터를 불러오는 중...'):
        df = get_flight_data(api_key_input, gate_input, selected_terminals)
    
    # 결과가 없을 때
    if df.empty:
        st.error("조건에 맞는 비행 스케줄이 없습니다.")
        st.info("💡 팁: 게이트 번호에 비행기가 없거나, 키 등록 대기중(1시간 소요)일 수 있습니다.")
        
        # 디버깅용 링크 제공
        real_key = unquote(api_key_input)
        test_link = f"http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getStatusOfAllFltDeOdp?serviceKey={real_key}&type=json&searchTerminalId=P01&numOfRows=5&pageNo=1"
        st.markdown(f"[👉 클릭해서 데이터가 뜨는지 확인해보기 (테스트 링크)]({test_link})")
        
    else:
        # 결과가 있을 때 (시간순 정렬)
        st.success(f"총 {len(df)}건의 스케줄을 찾았습니다.")
        
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')
            
        for index, row in df.iterrows():
            # 변수 추출
            row_type = row.get('type', '출발')
            time_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{time_str[8:10]}:{time_str[10:12]}" if len(time_str) >= 12 else "미정"
            
            remark = row.get('remark', '')
            if not remark: remark = "예정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            airport = row.get('airport', '-')
            gate = row.get('gate', '?')
            
            # 색상 및 아이콘 결정
            if row_type == '도착':
                bg_color = "#e7f5ff" # 파랑 배경 (도착)
                border_color = "#004085"
                icon = "🛬 IN"
                route_str = f"출발지: {airport}"
            else:
                # 출발 상태별 색상
                if "탑승" in remark:
                    bg_color = "#d4edda" # 초록 (탑승중)
                    border_color = "#155724"
                    icon = "🟢 OUT"
                elif "마감" in remark or "Final" in remark:
                    bg_color = "#f8d7da" # 빨강 (마감)
                    border_color = "#721c24"
                    icon = "🔴 OUT"
                elif "지연" in remark:
                    bg_color = "#fff3cd" # 노랑 (지연)
                    border_color = "#856404"
                    icon = "🟡 OUT"
                else:
                    bg_color = "#ffffff" # 흰색 (대기)
                    border_color = "#ccc"
                    icon = "🛫 OUT"
                route_str = f"목적지: {airport}"

            # HTML 카드 출력 (안전하게 분리)
            card_html = f"""
            <div style="
                padding: 15px; 
                margin-bottom: 12px; 
                border-radius: 10px; 
                background-color: {bg_color}; 
                border: 1px solid {border_color};
                box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 22px; font-weight: bold; color: #333;">{f_time}</span>
                    <span style="font-size: 16px; font-weight: bold; color: #333;">{remark}</span>
                </div>
                <div style="font-size: 18px; margin-bottom: 5px;">
                    <span style="background-color: #333; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 14px; margin-right: 5px;">G{gate}</span>
                    <b>{flight_no}</b>
                </div>
                <div style="font-size: 14px; color: #555;">
                    <b>{icon}</b> | {airline} <br>
                    {route_str}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
