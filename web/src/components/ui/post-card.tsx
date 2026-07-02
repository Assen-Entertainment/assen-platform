import * as React from "react";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/ui/avatar";
import { HeartIcon, HeartFilledIcon, CommentIcon, ShareIcon, MoreIcon } from "@/lib/icons";

/** PostCard — Figma DS(25:15). 피드 포스트. [브랜드 루브릭] C: 크리에이터 행 강조. 아이콘=Material(react-icons/md). */
export interface PostCardProps extends React.HTMLAttributes<HTMLElement> {
  creatorName: string;
  creatorMeta?: string;
  avatarSrc?: string;
  avatarFallback?: string;
  verified?: boolean;
  body?: string;
  media?: React.ReactNode;
  likeCount?: number;
  commentCount?: number;
  liked?: boolean;
  onLike?: () => void;
  onComment?: () => void;
  onShare?: () => void;
  onMore?: () => void;
}

const ico = "size-5 shrink-0";

export const PostCard = React.forwardRef<HTMLElement, PostCardProps>(
  (
    { creatorName, creatorMeta, avatarSrc, avatarFallback, verified, body, media, likeCount, commentCount, liked, onLike, onComment, onShare, onMore, className, ...props },
    ref,
  ) => (
    <article ref={ref} className={cn("flex w-full flex-col gap-3 border-b border-outline bg-surface p-4", className)} {...props}>
      <header className="flex items-center gap-3">
        <Avatar src={avatarSrc} fallback={avatarFallback} size="md" verified={verified} />
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="line-clamp-1 text-label text-on-surface">{creatorName}</span>
          {creatorMeta ? <span className="line-clamp-1 text-caption text-on-surface-variant">{creatorMeta}</span> : null}
        </div>
        <button type="button" aria-label="더보기" onClick={onMore} className="flex size-8 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high [&>svg]:size-5">
          <MoreIcon />
        </button>
      </header>
      {body ? <p className="whitespace-pre-wrap text-body-m text-on-surface">{body}</p> : null}
      {media ? <div className="overflow-hidden rounded-md">{media}</div> : null}
      <div className="flex items-center gap-5 text-on-surface-variant">
        <button
          type="button"
          onClick={onLike}
          aria-pressed={liked}
          aria-label={`좋아요 ${likeCount ?? 0}개`}
          className={cn("inline-flex items-center gap-1.5 text-body-s transition-colors hover:text-on-surface", liked && "text-error")}
        >
          {liked ? <HeartFilledIcon className={ico} /> : <HeartIcon className={ico} />} {likeCount ?? 0}
        </button>
        <button
          type="button"
          onClick={onComment}
          aria-label={`댓글 ${commentCount ?? 0}개`}
          className="inline-flex items-center gap-1.5 text-body-s transition-colors hover:text-on-surface"
        >
          <CommentIcon className={ico} /> {commentCount ?? 0}
        </button>
        <button type="button" aria-label="공유" onClick={onShare} className="inline-flex items-center transition-colors hover:text-on-surface">
          <ShareIcon className={ico} />
        </button>
      </div>
    </article>
  ),
);
PostCard.displayName = "PostCard";
