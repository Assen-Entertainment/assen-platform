import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ── 1. Hero 등장 타임라인 ── */
if (!reduced) {
  const intro = gsap.timeline({ defaults: { ease: 'back.out(1.6)' } });
  intro
    .from('.site-header', { y: -60, opacity: 0, duration: 0.5, ease: 'power2.out' })
    .from('.hero-kicker .badge-chip', { y: 18, opacity: 0, stagger: 0.08, duration: 0.4 }, '-=0.1')
    .from('.hero-title .line', { yPercent: 110, duration: 0.7, stagger: 0.12, ease: 'power3.out' }, '-=0.2')
    .from('.hero-sub, .hero-actions, .hero-stamps', { y: 24, opacity: 0, stagger: 0.1, duration: 0.5, ease: 'power2.out' }, '-=0.3')
    .from('.float-phone', { y: 80, opacity: 0, rotate: 4, duration: 0.8, ease: 'power3.out' }, '-=0.6')
    .from('.float-cheki', { scale: 0, opacity: 0, rotate: () => gsap.utils.random(-20, 20), stagger: 0.12, duration: 0.6 }, '-=0.5')
    .from('.sticker', { scale: 0, opacity: 0, stagger: 0.1, duration: 0.5, ease: 'elastic.out(1, 0.5)' }, '-=0.3')
    .from('.confetti', { scale: 0, opacity: 0, stagger: 0.04, duration: 0.4 }, '-=0.6');

  /* 떠다니는 idle 모션 */
  gsap.utils.toArray('.float-cheki').forEach((el, i) => {
    gsap.to(el, { y: i % 2 === 0 ? -14 : 12, duration: 2.6 + i * 0.5, yoyo: true, repeat: -1, ease: 'sine.inOut' });
  });
  gsap.to('.sticker-heart', { rotate: 8, scale: 1.08, duration: 1.4, yoyo: true, repeat: -1, ease: 'sine.inOut' });
  gsap.utils.toArray('.confetti').forEach((el, i) => {
    gsap.to(el, { y: gsap.utils.random(-22, 22), x: gsap.utils.random(-12, 12), duration: gsap.utils.random(2.4, 4.2), yoyo: true, repeat: -1, ease: 'sine.inOut', delay: i * 0.15 });
  });

  /* 마우스 패럴랙스 */
  const stage = document.querySelector('.hero-stage');
  if (stage && window.matchMedia('(pointer: fine)').matches) {
    document.querySelector('.hero').addEventListener('mousemove', (e) => {
      const dx = (e.clientX / window.innerWidth - 0.5);
      const dy = (e.clientY / window.innerHeight - 0.5);
      gsap.to('.float-phone', { x: dx * 10, y: dy * 8, duration: 0.6, overwrite: 'auto' });
      gsap.to('.ch1', { x: dx * 26, y: dy * 20, duration: 0.8, overwrite: 'auto' });
      gsap.to('.ch2', { x: dx * -32, y: dy * -22, duration: 0.8, overwrite: 'auto' });
      gsap.to('.ch3', { x: dx * 20, y: dy * -16, duration: 0.8, overwrite: 'auto' });
    });
  }
}

/* ── 2. 마퀴 무한 루프 ── */
if (!reduced) {
  const track = document.querySelector('.marquee-track');
  if (track) {
    const half = track.scrollWidth / 2;
    gsap.to(track, { x: -half, duration: 22, ease: 'none', repeat: -1 });
  }
}

/* ── 3. 섹션 리빌 ── */
gsap.utils.toArray('[data-reveal]').forEach((el) => {
  gsap.from(el, {
    y: reduced ? 0 : 60,
    opacity: 0,
    duration: 0.8,
    ease: 'power3.out',
    scrollTrigger: { trigger: el, start: 'top 78%' },
  });
});
gsap.utils.toArray('.feature-row').forEach((row) => {
  const stage = row.querySelector('.feature-stage .phone');
  const deco = row.querySelectorAll('.deco-cheki, .deco-card, .sticker-stamp');
  if (!stage || reduced) return;
  gsap.from(stage, {
    y: 70, rotate: row.classList.contains('reverse') ? -5 : 5, opacity: 0,
    duration: 0.9, ease: 'power3.out',
    scrollTrigger: { trigger: row, start: 'top 70%' },
  });
  if (deco.length) {
    gsap.from(deco, {
      scale: 0, opacity: 0, duration: 0.6, ease: 'back.out(2)', delay: 0.3, stagger: 0.1,
      scrollTrigger: { trigger: row, start: 'top 70%' },
    });
  }
});

/* ── 4. 스탬프 보드 — 도장 쾅쾅 ── */
const slots = gsap.utils.toArray('.board-slot[data-stamp]');
if (slots.length) {
  ScrollTrigger.create({
    trigger: '.stamp-board',
    start: 'top 75%',
    once: true,
    onEnter: () => {
      slots.forEach((slot, i) => {
        gsap.fromTo(
          slot,
          { scale: 1 },
          { keyframes: [{ scale: 1.18, duration: 0.12 }, { scale: 1, duration: 0.18 }], delay: i * 0.16, ease: 'power2.out' }
        );
        gsap.delayedCall(i * 0.16 + 0.06, () => slot.classList.add('stamped'));
      });
    },
  });
}

/* ── 5. 카운터 ── */
gsap.utils.toArray('[data-count]').forEach((el) => {
  const target = parseInt(el.dataset.count, 10);
  const obj = { v: 0 };
  ScrollTrigger.create({
    trigger: el,
    start: 'top 85%',
    once: true,
    onEnter: () =>
      gsap.to(obj, {
        v: target,
        duration: reduced ? 0 : 1.4,
        ease: 'power2.out',
        onUpdate: () => { el.textContent = Math.round(obj.v); },
      }),
  });
});
