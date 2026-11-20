export interface Member {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  join_date: string;
  is_active: boolean;
}

export type MemberFormValues = Omit<Member, "id">;
