import streamlit as st
import requests
import pandas as pd
from urllib.parse import unquote
from datetime import datetime

# ==========================================
# 1. 화면 설정
# ==========================================
st.set_page_config(page_title="PBB 에러 확인", page_icon="🚨")
st.title("🚨 PBB 에러 정밀 확인")
st.caption("End Point: statusOfAllFltDeOdp 적용됨")

# ==========================================
# 2. 사이드바
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    api_key_input = st.text_input("인증키 입력 (Decoding 권장)", type="password")
    
    # 터미널 선택
    terminal_options = {'T1': 'P01', '탑승동': 'P02', 'T2': 'P03'}
    selected_terminals = st.multiselect("구역", list(terminal_options.keys()), default=list(terminal_options.keys()))
    
    # 게이트 입력
    gate_input = st.text_input("게이트 번호 (비워두면 전체)", value="")
    
    if st.button("데이터 조회 시작"):
        st.rerun()

# ==========================================
# 3. 데이터 로직
# ==========================================
def get_flight_data(key_input, gate_input_str, terminals_to_check):
    if not key_input: return pd.DataFrame(), ["키를 입력해주세요."]

    real_key = unquote(key_input)
    today_str = datetime.now().strftime("%Y%m%d") # 예: 20260208
    
    # 게이트 정리
    target_gates = []
    if gate_input_str.strip():
        target_gates = [g.strip() for g in gate_input_str.split(',') if g.strip()]

    # 👇 [수정됨] 선생님이 알려주신 End Point + API 목록 조합
    base_url = "http://apis.data.go.kr/B551177/statusOfAllFltDeOdp"
    url_dep = f"{base_url}/getFltDeparturesDeOdp" # 출발
    url_arr = f"{base_url}/getFltArrivalsDeOdp"   # 도착
    
    all_flights = []
    error_logs = [] # 에러를 담을 그릇

    for t_name in terminals_to_check:
        t_code = terminal_options[t_name]
        
        # 파라미터 (날짜 포함)
        params = {
            "serviceKey": real_key,
            "type": "json",
            "terminalId": t_code,   # 설명서대로 terminalId 사용
            "searchDate": today_str, # 날짜 필수
            "numOfRows": "100",
            "pageNo": "1"
        }

        # --- [1] 출발 요청 ---
        try:
            res = requests.get(url_dep, params=params, timeout=10)
            if res.status_code == 200:
                try:
                    data = res.json()
                    items = data['response']['body']['items']
                    if items:
                        if not isinstance(items, list): items = [items]
                        for item in items:
                            current_gate = str(item.get('gate', ''))
                            if not target_gates or current_gate in target_gates:
                                item['type'] = '출발'
                                item['terminal_name'] = t_name
                                all_flights.append(item)
                except:
                    # JSON 파싱 실패 시 (에러 메시지가 텍스트로 온 경우)
                    error_logs.append(f"[{t_name} 출발 에러] {res.text[:300]}")
            else:
                error_logs.append(f"[{t_name} 출발 HTTP 에러] 상태코드: {res.status_code}")
        except Exception as e:
            error_logs.append(f"[{t_name} 출발 통신 에러] {e}")

        # --- [2] 도착 요청 ---
        try:
            res = requests.get(url_arr, params=params, timeout=10)
            if res.status_code == 200:
                try:
                    data = res.json()
                    items = data['response']['body']['items']
                    if items:
                        if not isinstance(items, list): items = [items]
                        for item in items:
                            current_gate = str(item.get('gate', ''))
                            if not target_gates or current_gate in target_gates:
                                item['type'] = '도착'
                                item['terminal_name'] = t_name
                                all_flights.append(item)
                except:
                    pass # 도착 에러는 로그 생략 (화면 너무 복잡해짐)
        except: pass

    return pd.DataFrame(all_flights), error_logs

# ==========================================
# 4. 화면 출력 (에러명 보여주기 기능 추가)
# ==========================================
if not api_key_input:
    st.warning("👈 키를 입력하세요.")
else:
    with st.spinner('서버와 통신 중...'):
        df, errors = get_flight_data(api_key_input, gate_input, selected_terminals)

    # 1. 에러가 있으면 가장 먼저 빨간색으로 보여줌
    if errors:
        st.error("🚨 서버에서 에러 메시지가 왔습니다!")
        for err in errors:
            st.code(err) # 에러명을 그대로 출력
        st.markdown("---")

    # 2. 데이터 출력
    if df.empty:
        if not errors:
            st.info("에러는 없지만 데이터가 비어있습니다.")
            st.write("(게이트 번호를 비우고 전체 조회를 해보세요)")
            
            # 링크 테스트
            real_key = unquote(api_key_input)
            today = datetime.now().strftime("%Y%m%d")
            test_url = f"http://apis.data.go.kr/B551177/statusOfAllFltDeOdp/getFltDeparturesDeOdp?serviceKey={real_key}&type=json&terminalId=P01&searchDate={today}&numOfRows=5&pageNo=1"
            st.markdown(f"[👉 클릭해서 직접 확인하기]({test_url})")
    else:
        if 'scheduleDateTime' in df.columns:
            df = df.sort_values(by='scheduleDateTime')

        count = len(df)
        st.success(f"✅ 데이터 수신 성공: 총 {count}건")

        for index, row in df.iterrows():
            row_type = row.get('type', '출발')
            gate = row.get('gate', '?')
            remark = row.get('remark', '예정')
            if not remark: remark = "예정"
            
            t_str = str(row.get('scheduleDateTime', ''))
            f_time = f"{t_str[8:10]}:{t_str[10:12]}" if len(t_str) >= 12 else "미정"
            
            flight_no = row.get('flightId', '-')
            airline = row.get('airline', '-')
            
            bg = "#e7f5ff" if row_type == '도착' else "#ffffff"
            icon = "🛬" if row_type == '도착' else "🛫"
            if "탑승" in remark: bg = "#d4edda"; icon = "🟢"
            
            st.markdown(f"""
            <div style="padding:15px; margin-bottom:10px; border-radius:10px; background-color:{bg}; border:1px solid #ccc;">
                <b>{f_time}</b> | {icon} {remark} | G{gate} | {flight_no}
            </div>
            """, unsafe_allow_html=True)
