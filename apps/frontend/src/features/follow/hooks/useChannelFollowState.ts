"use client";

import { useEffect, useRef, useState } from "react";
import { deleteFollow, getFollowStatus } from "@/features/follow/lib/followApi";

interface ChannelFollowState {
  isFollowing: boolean;
  isLoading: boolean;
  confirmingUnfollow: boolean;
  unfollow: () => void;
  refetch: () => Promise<void>;
}

export function useChannelFollowState(channelSlug: string): ChannelFollowState {
  const [isFollowing, setIsFollowing] = useState(false);
  const [followId, setFollowId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [confirmingUnfollow, setConfirmingUnfollow] = useState(false);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function fetch() {
    const status = await getFollowStatus(channelSlug);
    setIsFollowing(status.following);
    setFollowId(status.follow_id);
    setIsLoading(false);
  }

  useEffect(() => {
    fetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelSlug]);

  // Clean up timer on unmount.
  useEffect(() => () => {
    if (confirmTimerRef.current) clearTimeout(confirmTimerRef.current);
  }, []);

  function unfollow() {
    if (!followId) return;

    if (!confirmingUnfollow) {
      // First tap — open a 2-second confirmation window.
      setConfirmingUnfollow(true);
      confirmTimerRef.current = setTimeout(() => {
        setConfirmingUnfollow(false);
      }, 2000);
      return;
    }

    // Second tap within window — fire.
    clearTimeout(confirmTimerRef.current!);
    setConfirmingUnfollow(false);
    setIsFollowing(false);
    setFollowId(null);
    deleteFollow(followId).catch(() => fetch()); // revert on error
  }

  return { isFollowing, isLoading, confirmingUnfollow, unfollow, refetch: fetch };
}
