import { useMutation } from '@tanstack/react-query';
import { postOcr } from '@/lib/api';

export function useOcrJob() {
  return useMutation({ mutationFn: postOcr });
}

