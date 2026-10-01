// Weekly ownership is auxiliary evidence only; never enters stock/technical scores.
function ownershipMetrics(data, code, tradeDate) {
  const dates = Object.keys(data.weeks || {}).filter(d => !tradeDate || d <= tradeDate).sort();
  const date = dates[dates.length - 1];
  const current = data.weeks?.[date]?.stocks?.[code];
  if (!current) return null;
  const previousDate = dates[dates.length - 2];
  const previous = data.weeks?.[previousDate]?.stocks?.[code];
  function streak(field) {
    if (!previous) return null;
    let count = 0;
    for (let i = dates.length - 1; i > 0; i--) {
      const a = data.weeks[dates[i]]?.stocks?.[code]?.[field];
      const b = data.weeks[dates[i - 1]]?.stocks?.[code]?.[field];
      if (!Number.isFinite(a) || !Number.isFinite(b) || a <= b) break;
      count++;
    }
    return count;
  }
  return { ...current, date, previousDate: previous ? previousDate : null,
    delta400: previous ? current.over400_pct - previous.over400_pct : null,
    delta1000: previous ? current.over1000_pct - previous.over1000_pct : null,
    deltaPeople: previous ? current.total_people - previous.total_people : null,
    streak400: streak('over400_pct'), streak1000: streak('over1000_pct') };
}

async function showPKOwnership(stockData, history, tradeDate) {
  const el = document.getElementById('pk-ownership');
  if (!el) return;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let focus = [
    {role: '👤 我的PK', code: '2408', stock: '南亞科'},
    {role: '🤖 伙計PK', code: '2308', stock: '台達電'},
    {role: '⭐ 系統PK', code: '2317', stock: '鴻海'}
  ];
  let round = 3;
  try {
    const response = await fetch('pk.json?v=' + Date.now());
    if (response.ok) {
      const pk = await response.json();
      const record = (pk.records || []).filter(r => Number(r.round) >= 3).sort((a,b) => b.round-a.round)[0];
      if (record) {
        round = record.round;
        focus = [['user','👤 我的PK'],['partner','🤖 伙計PK'],['benchmark','⭐ 系統PK']]
          .map(([key,role]) => ({role, ...record[key]})).filter(s => s.code);
      }
    }
    const responseData = await fetch('ownership.json?v=' + Date.now());
    if (!responseData.ok) throw new Error('No ownership data');
    const data = await responseData.json();
    const pp = value => value == null ? '累積中' : (value > 0 ? '+' : '') + value.toFixed(2) + ' 個百分點';
    const people = value => value == null ? '累積中' : (value > 0 ? '+' : '') + value.toLocaleString() + ' 人';
    el.innerHTML = '<div class="section-title">🔎 第 ' + escape(round) + ' 戰｜集保籌碼輔助確認</div>' +
      '<p>每週持股快照，非每日買賣超。級距採「超過400張／超過1,000張」；不計入評分。</p>' +
      focus.map(item => {
        const m = ownershipMetrics(data, item.code, tradeDate);
        const title = '<strong>' + escape(item.role + '｜' + item.stock + ' ' + item.code) + '</strong>';
        if (!m) return '<div class="system-pick-card">' + title + '<p>尚無可用集保資料。</p></div>';
        const stale = tradeDate && (new Date(tradeDate + 'T00:00:00Z') - new Date(m.date + 'T00:00:00Z')) / 86400000 > 10;
        const stock = stockData[item.code];
        const number = value => value == null || String(value).trim() === '' ? NaN : Number(String(value).replace(/,/g,''));
        const net = stock ? number(stock.foreign) + number(stock.trust) : NaN;
        let signal = m.previousDate ? '持股趨勢尚未形成共振，維持觀察。' : '已建立首週基準；週增減與連增週數等待下一份資料。';
        if (stale) signal = '集保資料已超過10天，等待更新後再確認。';
        else if (m.delta400 > 0 && m.delta1000 > 0) {
          signal = '兩個大戶級距持股比例同步增加；';
          signal += Number.isFinite(net) ? (net > 0 ? '最新日外資＋投信偏買，作為集中趨勢的輔助確認。' : net < 0 ? '最新日外資＋投信偏賣，週與日訊號分歧。' : '最新日法人持平，等待價格確認。') : '最新日法人資料不足。';
        } else if (m.delta400 < 0 && m.delta1000 < 0) signal = '兩個大戶級距持股比例同步下降，留意籌碼分散。';
        return '<div class="system-pick-card">' + title +
          '<div class="pick-group">集保週日期：' + escape(m.date) + (m.previousDate ? '｜比較 ' + escape(m.previousDate) : '｜首週基準') +
          (stale ? '｜⚠️ 等待更新' : '') + '</div>' +
          '<div>超過400張：<strong>' + m.over400_pct.toFixed(2) + '%</strong>｜週變化 ' + pp(m.delta400) + '</div>' +
          '<div>超過1,000張：<strong>' + m.over1000_pct.toFixed(2) + '%</strong>｜週變化 ' + pp(m.delta1000) + '｜' + m.over1000_people.toLocaleString() + ' 人</div>' +
          '<div>比例連增：400張 ' + (m.streak400 == null ? '累積中' : m.streak400 + ' 週') + '／1,000張 ' + (m.streak1000 == null ? '累積中' : m.streak1000 + ' 週') + '</div>' +
          '<div>總股東人數：' + m.total_people.toLocaleString() + ' 人｜週變化 ' + people(m.deltaPeople) + '</div>' +
          '<div class="pick-block"><strong>③ 籌碼變化｜</strong>' + signal + '</div>' +
          '<div class="pick-group">法人對照日期：' + escape(tradeDate || '未知') + '（與集保週日期不同）</div></div>';
      }).join('') + '<p style="font-size:15px;color:#64748b">比例增減可能包含跨級距、配股與股本變動；不能直接換算成大戶買超。<a href="https://www.tdcc.com.tw/portal/zh/smWeb/qryStock" target="_blank" rel="noopener">集保官方資料</a></p>';
  } catch (error) {
    console.error('PK ownership unavailable', error);
    el.innerHTML = '<p>PK集保輔助資料暫時無法讀取；原有PK與評分照常顯示。</p>';
  }
}
