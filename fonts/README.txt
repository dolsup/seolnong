설농체 — Seolnong
Regular · Version 1.001

일본의 한국어 안내판에서 본 낯선 글자 모양을 바탕으로 만든 표시용 서체입니다.
안내판, 제목, 짧은 문구에 사용해 보세요.

설치
  Seolnong-Regular.ttf를 열어 운영체제의 글꼴 설치 기능으로 설치합니다.
  글꼴 목록에서 '설농체' 또는 'Seolnong'을 선택하세요.
  Seolnong-Regular.woff2는 웹사이트에서 사용하는 파일입니다.

지원 범위
  현대 한글 11,172자, 현대 조합 자모와 호환 자모, 기본 영문·숫자·기호.
  Regular 한 굵기입니다. 한자·일본어·옛한글은 별도 글꼴을 함께 사용하세요.

대체 자형
  기본형은 ㅎ·ㅊ의 짧은 가로 꼭지입니다.
  OpenType 스타일 세트 ss01을 켜면 두 자모의 꼭지가 함께 세로로 바뀝니다.
  앱에서는 'Upright Caps / 세로 꼭지 ㅎ·ㅊ'를 선택하세요.

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

라이선스
  SIL Open Font License 1.1. 개인·상업 이용, 수정과 재배포가 가능합니다.
  재배포할 때에는 OFL.txt의 저작권 고지와 라이선스 전문을 함께 유지하세요.
  정확한 조건은 동봉한 OFL.txt를 따릅니다.

Copyright (c) 2026 The Seolnong Sign Project Authors.
