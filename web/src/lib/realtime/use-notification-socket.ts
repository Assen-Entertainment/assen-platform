"use client";
// 실시간 알림 소켓(R4-W4) — 서버 Channels WS(ws/notifications) 소비.
//
// 우아한 저하(회귀 0): config.wsUrl(NEXT_PUBLIC_WS_URL) 미설정이면 완전 no-op —
// WebSocket을 아예 만들지 않고 기존 폴백(useNotifications 조회/invalidate) 동작을 그대로 둔다.
// 빌드/CI/스모크 기본이 미설정이므로 그 환경에선 실시간 기능이 켜지지 않는다.
//
// ⚠️ WS는 Next rewrites로 프록시되지 않아 별도 오리진 env(config.wsUrl)가 필수다.
//    인증은 httpOnly `assen_access` 쿠키(동일 도메인이면 브라우저가 credentialed WS로 자동 송신 —
//    별도 헤더 주입 불가). 미인증 핸드셰이크는 서버가 close 4401로 끊으며, 이때는 재연결하지 않고
//    세션 가드(로그아웃/재인증)에 맡긴다.
//
// 서버→클라 메시지:
//  • {"type":"unread_count","count":int}         접속 직후 1회 — 뱃지 카운트 동기화
//  • {"type":"notification","notification":{…}}   알림 발생 — 뱃지 +1 + 목록 무효화 + 토스트
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { config } from "@/lib/config";
import { qk } from "@/lib/api/queries";
import { onNotificationsRead } from "@/lib/api/notification-events";
import { useSession } from "@/lib/session";
import { useToast } from "@/components/ui/use-toast";
import type { NotificationKind } from "@/lib/api";

/** 서버 WS 알림 페이로드(notification 메시지). 목록 Notification과 달리 원본 created_at만 온다. */
interface SocketNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  href?: string;
  created_at?: string;
}

/** 재연결 지수 백오프 상한(ms). */
const MAX_BACKOFF_MS = 30_000;

/**
 * 실시간 알림 소켓 훅 — 셸에서 1회 마운트. 반환값은 미읽음 뱃지 카운트.
 * config.wsUrl 미설정 또는 비로그인 시 0을 반환하고 아무 연결도 하지 않는다(no-op·회귀 0).
 */
export function useNotificationSocket(): number {
  const { user } = useSession();
  const userId = user?.id;
  const qc = useQueryClient();
  const { toast } = useToast();
  const [unreadCount, setUnreadCount] = React.useState(0);

  // 읽음 뮤테이션 통지 구독(셸 1회 마운트) — 소켓 카운트를 감소/재동기해 스테일-하이를 막는다.
  // WS 미설정 시 unreadCount는 항상 0이라 감소도 no-op → 회귀 0(기존 뱃지 동작 보존).
  React.useEffect(() => {
    return onNotificationsRead((e) => {
      setUnreadCount((c) => (e.type === "all" ? 0 : Math.max(0, c - 1)));
    });
  }, []);

  React.useEffect(() => {
    // 게이트: WS URL 미설정(기본) 또는 비로그인 → 완전 no-op. 로그아웃 시 뱃지도 리셋.
    if (!config.wsUrl || !userId) {
      setUnreadCount(0);
      return;
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0; // 지수 백오프 시도 횟수(open 성공 시 0으로 리셋)
    let disposed = false; // 언마운트/로그아웃 — 재연결 중단
    let authFailed = false; // close 4401 — 재연결 중단(세션 가드가 처리)

    const handleMessage = (raw: string) => {
      let msg: unknown;
      try {
        msg = JSON.parse(raw);
      } catch {
        return; // 파싱 불가 메시지 무시
      }
      if (!msg || typeof msg !== "object") return;
      const m = msg as { type?: string; count?: number; notification?: SocketNotification };
      if (m.type === "unread_count" && typeof m.count === "number") {
        // 접속 직후 서버 권위 카운트로 뱃지 동기화(음수 방어).
        setUnreadCount(Math.max(0, m.count));
      } else if (m.type === "notification" && m.notification) {
        // 새 알림: 뱃지 +1 + 목록 캐시 무효화(다음 조회 시 최신화) + 토스트.
        setUnreadCount((c) => c + 1);
        void qc.invalidateQueries({ queryKey: qk.notifications });
        toast({ title: m.notification.title });
      }
    };

    const connect = () => {
      if (disposed) return;
      // credentialed WS — 동일 도메인이면 브라우저가 httpOnly 쿠키를 자동 송신(별도 헤더 불가).
      const ws = new WebSocket(config.wsUrl);
      socket = ws;
      ws.onopen = () => {
        attempt = 0; // 연결 성공 — 백오프 리셋
      };
      ws.onmessage = (ev: MessageEvent) => {
        handleMessage(typeof ev.data === "string" ? ev.data : "");
      };
      ws.onclose = (ev: CloseEvent) => {
        if (disposed) return;
        // 4401 = 인증 만료/미인증 — 재연결하지 않는다(세션 가드가 처리).
        if (ev.code === 4401) {
          authFailed = true;
          return;
        }
        if (authFailed) return;
        // 그 외 비정상 종료 → 지수 백오프(상한 MAX_BACKOFF_MS)로 재연결.
        const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** attempt);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      // 언마운트/로그아웃/유저 변경 — 소켓·타이머 정리(중복 연결 방지).
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) {
        socket.onclose = null; // 정리 중 재연결 스케줄 방지
        socket.close();
      }
    };
    // 실질 트리거는 userId(로그인/로그아웃/계정 전환). qc·toast는 컨텍스트 안정 참조라 재연결 churn 없음.
  }, [userId, qc, toast]);

  return unreadCount;
}
