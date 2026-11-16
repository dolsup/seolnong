(() => {
  'use strict';
  const presets = {
    lodging: '야간의 체크인은 프런트 옆의 벨을 눌러 주십시오.\n휴게실의 물과 커피는 무료로 준비하고 있습니다.',
    rental: '예약의 변경은 이쪽에서 부탁합니다.\n빌린 물품은 물기를 닦고 돌려 주십시오.\n젖은 그대로 가방에 넣는 것은 삼가 주십시오.',
    freezer: '품절의 때는 옆의 매점을 이용해 주십시오.\n냉동고의 뚜껑은 조용히 닫아 주십시오.\n얼음만 가지고 돌아가는 것은 삼가 주십시오.',
    pangram: '컴퓨터 비밀번호의 별표만 훔쳐서야 도둑질은 되나?',
    notice: '사용후는 화장지를 흘려주세요',
    shopping: '상품에는 손을 대지 말아주세요.\n계산은 이쪽에서 부탁합니다.',
    bath: '【이용의 안내】\n입욕료 ¥500　수온 42℃\n※ 이 물은 마실 수 없습니다.',
    name: '설농탕'
  };
  const input = document.querySelector('#type-input');
  const select = document.querySelector('#sample-preset');
  const size = document.querySelector('#type-size');
  const caps = document.querySelector('#upright-toggle');
  const proportional = document.querySelector('#proportional-toggle');
  const slashedZero = document.querySelector('#zero-toggle');
  const vertical = document.querySelector('#vertical-toggle');
  const status = document.querySelector('#font-status');
  const defaultSize = () => window.matchMedia('(max-width:760px)').matches ? 32 : 48;
  let composing = false;
  size.value = defaultSize();

  function fitHeight() {
    if (vertical.checked) {
      input.style.height = `${window.innerWidth <= 760 ? 360 : 420}px`;
      return;
    }
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, window.innerWidth <= 760 ? 600 : 750)}px`;
  }
  function render() {
    input.style.fontSize = `${size.value}px`;
    input.dataset.caps = caps.checked ? '1' : '0';
    input.dataset.direction = vertical.checked ? 'vertical' : 'horizontal';
    input.style.fontFeatureSettings = `"ss01" ${caps.checked ? 1 : 0}, "pnum" ${proportional.checked ? 1 : 0}, "tnum" ${proportional.checked ? 0 : 1}, "zero" ${slashedZero.checked ? 1 : 0}`;
    document.querySelector('#size-value').textContent = size.value;
    const text = input.value.normalize('NFC');
    select.value = Object.keys(presets).find(key => presets[key] === text) || 'custom';
    fitHeight();
  }
  function normalizeInput() {
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const value = input.value;
    const normalized = value.normalize('NFC');
    if (value !== normalized) {
      input.value = normalized;
      input.setSelectionRange(value.slice(0,start).normalize('NFC').length, value.slice(0,end).normalize('NFC').length);
    }
  }
  input.addEventListener('compositionstart', () => {composing = true;});
  input.addEventListener('compositionend', () => {composing = false; normalizeInput(); render();});
  input.addEventListener('input', () => {if (!composing) render(); else fitHeight();});
  input.addEventListener('blur', () => {normalizeInput(); render();});
  select.addEventListener('change', () => {if (presets[select.value]) {input.value = presets[select.value]; render();}});
  size.addEventListener('input', render);
  caps.addEventListener('change', render);
  proportional.addEventListener('change', render);
  slashedZero.addEventListener('change', render);
  vertical.addEventListener('change', render);
  document.querySelector('#reset-type').addEventListener('click', () => {
    input.value = presets.lodging;
    size.value = defaultSize();
    caps.checked = proportional.checked = slashedZero.checked = vertical.checked = false;
    render();
  });
  window.addEventListener('resize', fitHeight, {passive:true});
  render();

  function revealUpdates() {
    if (window.location.hash !== '#updates') return;
    const details = document.querySelector('#updates').closest('details');
    details.open = true;
    window.requestAnimationFrame(() => details.scrollIntoView({block:'start'}));
  }
  window.addEventListener('hashchange', revealUpdates);
  revealUpdates();

  async function loadFonts() {
    if (!document.fonts) {status.textContent='';return;}
    try {
      await document.fonts.ready;
      const results = await Promise.all([
        document.fonts.load('20px "Seolnong"', 'Station Plaza Civic Hall'),
        document.fonts.load('40px "Seolnong KR"', '설농탕하차꽃'),
        document.fonts.load('40px "Seolnong KR Upright"', '하차꽃'),
        document.fonts.load('40px "Kosugi Maru"', '雪濃湯お手洗い'),
        document.fonts.load('26px "Arimo"', 'Station Plaza Civic Hall')
      ]);
      if (results.some(faces => !faces.length || faces.some(face => face.status !== 'loaded'))) throw new Error('Font unavailable');
      status.textContent='';
      status.dataset.state='ready';
      document.documentElement.dataset.fonts='ready';
      fitHeight();
    } catch (_) {status.textContent='書体を読み込めません。再読み込みしてください。 / 서체를 읽을 수 없습니다. 다시 읽어 주십시오.';status.dataset.state='error';}
  }
  loadFonts();
})();
