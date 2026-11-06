/* 六十四卦元数据（通行本卦序 + 由索引派生的上下卦与六爻编码）
 * 索引与 gua-data.js 完全一致：idx = 上卦 * 8 + 下卦，下爻为低位。
 * 卦名、卦辞、爻辞只来自 gua-data.js，本文件不另存一套文案。
 * 卦序底本：通行本（王弼注本）卦序，与朱熹《周易本义》一致。
 */
window.GUA_KINGWEN = [
   2, 24,  7, 19, 15, 36, 46, 11,
  16, 51, 40, 54, 62, 55, 32, 34,
   8,  3, 29, 60, 39, 63, 48,  5,
  45, 17, 47, 58, 31, 49, 28, 43,
  23, 27,  4, 41, 52, 22, 18, 26,
  35, 21, 64, 38, 56, 30, 50, 14,
  20, 42, 59, 61, 53, 37, 57,  9,
  12, 25,  6, 10, 33, 13, 44,  1
];
/* 六爻皆动的乾坤专用辞（通行本） */
window.GUA_YONG = {
  '乾为天': { label: '用九', text: '见群龙无首，吉。' },
  '坤为地': { label: '用六', text: '利永贞。' }
};
(function(){
  var TRI = window.BAGUA || ['坤','震','坎','兑','艮','离','巽','乾'];
  window.GUA_DATA.forEach(function(g, i){
    var lower = i % 8, upper = (i - lower) / 8;
    g.idx = i;
    g.no = window.GUA_KINGWEN[i];
    g.upperTri = TRI[upper];
    g.lowerTri = TRI[lower];
    g.bits = [lower & 1, (lower >> 1) & 1, (lower >> 2) & 1,
              upper & 1, (upper >> 1) & 1, (upper >> 2) & 1];
    g.lt = g.bits.map(function(b, k){
      var p = ['初','二','三','四','五','上'][k];
      return (k === 0 || k === 5) ? p + (b ? '九' : '六') : (b ? '九' : '六') + p;
    });
  });
})();
