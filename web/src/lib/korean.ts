/**
 * 한글 조사(받침 의존) 헬퍼 — 리추얼 마이크로카피의 자연스러운 조사 선택용.
 * 마지막 글자가 한글 음절이면 종성(받침) 유무로 판단하고, 한글이 아니면 받침 없음(모음 뒤)으로 처리한다.
 */

const HANGUL_START = 0xac00;
const HANGUL_END = 0xd7a3;

/** 마지막 글자에 받침(종성)이 있으면 true. 한글 음절이 아니면 false. */
export function hasCoda(word: string): boolean {
  const ch = (word ?? "").trim().slice(-1);
  if (!ch) return false;
  const code = ch.charCodeAt(0);
  if (code < HANGUL_START || code > HANGUL_END) return false;
  return (code - HANGUL_START) % 28 !== 0;
}

/** 와/과 — 받침 있으면 "과", 없으면 "와"("별빛 일러스트와" · "토끼방송국과"). */
export function waGwa(word: string): "와" | "과" {
  return hasCoda(word) ? "과" : "와";
}
