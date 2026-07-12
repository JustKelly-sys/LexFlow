/** Shared types used across the LexFlow frontend */

export interface UserProfile {
  full_name?: string;
  firm_name?: string;
  hourly_rate?: number;
  onboarded?: boolean;
}

export interface PendingReview {
  client_name: string;
  matter_description: string;
  duration: string;
  billable_amount: string;
  original_ai_output?: Record<string, string>;
}

export interface ExtractedEntry {
  client_name: string;
  matter_description: string;
  duration: string;
  billable_amount: string;
  [key: string]: string | undefined;
}
