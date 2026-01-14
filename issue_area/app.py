import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import platform
import matplotlib.font_manager as fm

# 웹 페이지 레이아웃 설정
st.set_page_config(page_title="배달 데이터 분석 대시보드", layout="wide")

st.title("📊 주차별 지역 배달 지표 분석")
st.sidebar.header("설정 및 필터")

# 1. 파일 업로드 기능
uploaded_file = st.sidebar.file_uploader("엑셀/CSV 파일을 업로드하세요", type=['xlsx', 'csv'])

if uploaded_file:
    # 데이터 읽기
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # 2. 필터링 수치 설정 (웹에서 조절 가능)
    min_cnt = st.sidebar.number_input("최소 배달건수 기준", value=1000)
    min_quality = st.sidebar.slider("최소 품질 지수 기준", 0.1, 5.0, 2.0)

    @st.cache_resource # 폰트 설정을 캐싱하여 속도 향상
    def set_korean_font():
        plt.rcParams['axes.unicode_minus'] = False
        system = platform.system()
        
        if system == 'Windows':
            plt.rc('font', family='Malgun Gothic')
        elif system == 'Darwin':
            plt.rc('font', family='AppleGothic')
        else:
            # Streamlit Cloud(Linux) 환경: 나눔고딕 설치 및 경로 지정
            # 보통 나눔고딕이 기본 설치되어 있지 않으므로 폰트 경로를 직접 체크하거나 
            # 시스템 폰트 목록에서 나눔을 찾아 설정합니다.
            try:
                # 폰트 매니저에 나눔고딕이 있는지 확인
                font_names = [f.name for f in fm.fontManager.ttflist]
                if 'NanumGothic' in font_names:
                    plt.rc('font', family='NanumGothic')
                else:
                    # 폰트가 없을 경우 대비하여 범용 폰트 설정
                    plt.rc('font', family='DejaVu Sans') 
            except:
                pass

    set_korean_font()

    df['지역'] = df['pickup_rgn1_nm'] + "_" + df['pickup_rgn2_nm']
    latest_week = df['part_week'].max()
    condition = (df['part_week'] == latest_week) & (df['dlvry_cnt_fact'] > min_cnt) & (df['dt60min_fact'] >= min_quality)
    target_regions = df[condition]['지역'].unique()
    df_filtered = df[df['지역'].isin(target_regions)].copy()

        # 4. 그래프 생성
    fig, ax = plt.subplots(figsize=(12, 8))

    # 5. 주차별 설정 (2주치 데이터 가정)
    weeks = sorted(df_filtered['part_week'].unique())
    colors = {weeks[0]: 'blue', weeks[1]: 'red'}


    # 3. 지역별 화살표 그리기 (파랑 -> 빨강 이동 경로)
    # target_regions는 필터링에서 살아남은 지역 리스트입니다.
    for region in df_filtered['지역'].unique():
        region_data = df_filtered[df_filtered['지역'] == region]
        
        # 해당 지역의 데이터가 2주치 모두 존재하는 경우에만 화살표를 그립니다.
        if len(region_data) == 2:
            # 지난주차(Start)와 이번주차(End) 데이터 추출
            start_node = region_data[region_data['part_week'] == weeks[0]].iloc[0]
            end_node = region_data[region_data['part_week'] == weeks[1]].iloc[0]
            
            # 화살표 그리기
            ax.annotate('', 
                        xy=(end_node['QSH 비중'], end_node['rider_cnt_error']), # 도착점
                        xytext=(start_node['QSH 비중'], start_node['rider_cnt_error']), # 시작점
                        arrowprops=dict(
                            arrowstyle='->', 
                            color='grey', 
                            lw=1.5, 
                            linestyle='--',
                            alpha=0.7, # 화살표 투명도 50%
                            mutation_scale=25 # 화살표 머리 크기
                        ))


    for week in weeks:
        week_data = df_filtered[df_filtered['part_week'] == week]
        
        # 산점도 그리기
        # s 파라미터에 배달건수를 넣어 크기 조절 (수치가 너무 크면 적절히 나눕니다, 예: / 10)
        ax.scatter(
            week_data['QSH 비중'], 
            week_data['rider_cnt_error'], 
            s=np.sqrt(week_data['dlvry_cnt_fact'])*2,  # 건수에 따른 크기 조절
            c=colors[week], 
            label=f'{week} 주차', 
            alpha=0.5, 
            edgecolors='w', 
            linewidths=0.5,
        )
        
        # 점 위에 지역명 표시
        for _, row in week_data.iterrows():
            ax.text(
                row['QSH 비중'], 
                row['rider_cnt_error'], 
                row['지역'], 
                fontsize=8, 
                ha='center', 
                va='center',
                fontweight='bold' if colors[week] == 'red' else 'normal'
            )

    # 4. ★ 범례 설정 (점 크기 고정) ★
    # markerscale을 조절하거나, handlelength 등을 사용하여 범례의 마커 크기를 고정합니다.
    lgnd = ax.legend(title='주차별 구분', loc='upper right', scatterpoints=1, fontsize=10)

    # 범례 내의 점 크기를 개별적으로 지정 (예: 50으로 고정)
    for handle in lgnd.legend_handles:
        handle._sizes = [70] 

    # 5. 축 설정 (평균선)
    ax.axvline(df_filtered['QSH 비중'].mean(), color='gray', linestyle='--', alpha=0.5)
    ax.axhline(df_filtered['rider_cnt_error'].mean(), color='gray', linestyle='--', alpha=0.5)

    # 6. 마무리
    ax.set_title(f'주차별 이슈지역', fontsize=15)
    ax.set_xlabel('QSH 비중(%)')
    ax.set_ylabel('ML수급율(%)')
    ax.grid(True, linestyle=':', alpha=0.3)

    # 4. 웹 화면에 그래프 출력
    st.pyplot(fig)
    
    # 데이터 테이블도 같이 보여주기
    st.subheader("필터링된 데이터 상세")
    st.dataframe(df_filtered)

else:
    st.info("왼쪽 사이드바에서 데이터를 업로드해주세요.")