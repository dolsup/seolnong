설농체 — Seolnong
Regular · Version 1.003

일본의 한국어 안내판에서 본 낯선 글자 모양을 바탕으로 만든 표시용 서체입니다.
안내판, 제목, 짧은 문구에 사용해 보세요.

1.003의 변경
  안내에 쓰는 괄호, 엔 기호, 주의·도형·온도 기호, 대각선 화살표 등을 더했습니다.
  세로쓰기 위치와 세로용 문장부호를 설계했습니다.
  대체 자형 선택, 비례 숫자, 사선이 든 0, 영문·문장부호 커닝을 추가했습니다.
  밑줄·취소선과 영문 높이 정보를 정리했습니다.
  같은 윤곽을 공유하도록 저장해 TTF·WOFF2 파일의 용량을 줄였습니다.
  기존 한글의 모양·폭과 ss01의 동작은 유지했습니다.

1.002의 변경
  '품·물·팔' 등에서 가까이 놓인 평행한 선의 간격을 조정했습니다.
  ㅑ·ㅕ·ㅒ·ㅖ의 가지 간격을 다듬었습니다.
  '설' 등 비스듬한 선이 가까이 오는 기존 모양은 유지했습니다.
  서체와 소개 페이지의 기본 견본 문장을 숙소 안내로 새로 넣었습니다.

설치
  Seolnong-Regular.ttf를 열어 운영체제의 글꼴 설치 기능으로 설치합니다.
  글꼴 목록에서 '설농체' 또는 'Seolnong'을 선택하세요.
  Seolnong-Regular.woff2는 웹사이트에서 사용하는 파일입니다.

지원 범위
  현대 한글 11,172자, 현대 조합 자모와 호환 자모, 기본 영문·숫자·기호.
  전각 영숫자·기호, 안내판용 괄호·화살표·통화·단위 기호를 포함합니다.
  Regular 한 굵기입니다. 한자·일본어·옛한글은 별도 글꼴을 함께 사용하세요.

대체 자형
  기본형은 ㅎ·ㅊ의 짧은 가로 꼭지입니다.
  OpenType 스타일 세트 ss01을 켜면 두 자모의 꼭지가 함께 세로로 바뀝니다.
  앱에서는 'Upright tops / 세로 꼭지 ㅎ·ㅊ'를 선택하세요.

추가 기능
  aalt: 지원 앱의 자형 패널에서 대체 모양을 고릅니다.
  pnum: 비례 폭 반각 숫자. tnum: 같은 폭 반각 숫자. 기본 숫자는 같은 폭입니다.
  zero: 숫자 0에 사선을 넣습니다.
  kern / vkrn: 가로·세로 조판에서 영문과 문장부호의 조합 간격을 보정합니다.
  vert / vrt2: 세로쓰기용 괄호·문장부호 등으로 바꿉니다.
  세로쓰기용 메트릭을 포함합니다. 기능의 선택 방법은 앱에 따라 다릅니다.

웹 사용 예
  @font-face {
    font-family: 'Seolnong';
    src: url('Seolnong-Regular.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
  }
  .sample {
    font-family: 'Seolnong', sans-serif;
    font-feature-settings: 'ss01' 0;
    font-synthesis: none;
  }
  세로 꼭지는 ss01 값을 1로 지정합니다.
  비례 숫자와 사선 0은 font-variant-numeric: proportional-nums slashed-zero;
  세로쓰기는 writing-mode: vertical-rl; text-orientation: mixed; 로 지정합니다.

라이선스
  SIL Open Font License 1.1. 개인·상업 이용, 수정과 재배포가 가능합니다.
  재배포할 때에는 OFL.txt의 저작권 고지와 라이선스 전문을 함께 유지하세요.
  정확한 조건은 동봉한 OFL.txt를 따릅니다.

Copyright (c) 2026 dolsup (https://github.com/dolsup/seolnong)
