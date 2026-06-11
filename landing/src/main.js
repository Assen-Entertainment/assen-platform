import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* 블록 단위 가드 — 한 블록이 죽어도 나머지 모션·콘텐츠는 산다 */
const safe = (fn) => {
  try { fn(); } catch (e) { console.error('[landing]', e); }
};

if (reduced) {
  /* ── 모션 OFF: 트윈을 아예 등록하지 않고 최종 상태를 즉시 적용 ── */
  document.querySelectorAll('[data-count]').forEach((el) => { el.textContent = el.dataset.count; });
  document.querySelectorAll('.board-slot[data-stamp]').forEach((el) => el.classList.add('stamped'));
} else {
  /* ── 1. Hero 등장 타임라인 ── */
  const heroTargets =
    '.site-header, .hero-kicker .badge-chip, .hero-title .line, .hero-sub, .hero-actions, .hero-stamps, .float-phone, .float-cheki, .sticker, .confetti';
  try {
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
  } catch (e) {
    /* 인트로 구성 중 실패 시 숨김 상태로 남지 않도록 인라인 스타일 제거 */
    console.error('[landing] hero intro failed, restoring visibility', e);
    gsap.set(heroTargets, { clearProps: 'all' });
  }

  safe(() => {
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
  });

  /* ── 2. 마퀴 무한 루프 ── */
  safe(() => {
    const track = document.querySelector('.marquee-track');
    if (track) {
      /* 트랙 = 동일한 절반 2개(index.html 참고) → 자기 폭 기준 -50%면 이음새 없는 루프.
         픽셀 측정과 달리 폰트 로드 후 폭이 바뀌어도 어긋나지 않는다 */
      gsap.to(track, { xPercent: -50, duration: 22, ease: 'none', repeat: -1 });
    }
  });

  /* ── 3. 섹션 리빌 ── */
  safe(() => {
    gsap.utils.toArray('[data-reveal]').forEach((el) => {
      gsap.from(el, {
        y: 60,
        opacity: 0,
        duration: 0.8,
        ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 78%' },
      });
    });
    gsap.utils.toArray('.feature-row').forEach((row) => {
      const stage = row.querySelector('.feature-stage .phone');
      const deco = row.querySelectorAll('.deco-cheki, .deco-card, .sticker-stamp, .mini-chip');
      if (!stage) return;
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
    /* 시작 4단계 — 순차 등장 */
    const steps = gsap.utils.toArray('.how-step');
    if (steps.length) {
      gsap.from(steps, {
        y: 44, opacity: 0, scale: 0.96,
        duration: 0.6, ease: 'back.out(1.5)', stagger: 0.12,
        scrollTrigger: { trigger: '.how-steps', start: 'top 76%' },
      });
    }
  });

  /* ── 4. 스탬프 보드 — 도장 쾅쾅 ── */
  safe(() => {
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
  });

  /* ── 5. 카운터 ── */
  safe(() => {
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
            duration: 1.4,
            ease: 'power2.out',
            onUpdate: () => { el.textContent = Math.round(obj.v); },
          }),
      });
    });
  });

  /* 폰트 스왑·이미지 로드 후 트리거 위치 재계산 */
  safe(() => {
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => ScrollTrigger.refresh());
    }
    window.addEventListener('load', () => ScrollTrigger.refresh());
  });
}

/* ── 모션 여부와 무관한 동작 ── */

/* 도트 내비 활성 표시 — IntersectionObserver (모션 설정과 무관) */
safe(() => {
  const dots = Array.from(document.querySelectorAll('.dot-nav a'));
  if (!dots.length || !('IntersectionObserver' in window)) return;
  const byId = new Map(dots.map((d) => [d.getAttribute('href').slice(1), d]));
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        dots.forEach((d) => d.classList.remove('active'));
        byId.get(en.target.id)?.classList.add('active');
      });
    },
    { rootMargin: '-45% 0px -45% 0px' }
  );
  byId.forEach((_, id) => {
    const section = document.getElementById(id);
    if (section) io.observe(section);
  });
});

/* 사전 등록 폼 — 백엔드 연결 전: 정직한 미리보기 안내 */
safe(() => {
  const form = document.querySelector('.cta-form');
  const success = document.querySelector('.cta-success');
  if (!form || !success) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = form.querySelector('input[type="email"]');
    if (email && !email.checkValidity()) {
      email.reportValidity();
      return;
    }
    form.hidden = true;
    success.hidden = false;
    if (!reduced) {
      gsap.from(success, { scale: 0.6, opacity: 0, rotate: -5, duration: 0.5, ease: 'back.out(2)' });
    }
  });
});
