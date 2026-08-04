export interface CurrentProfile {
  id: number
  username: string
  email: string
  display_name: string
  roles: string[]
  created_at: string
  updated_at: string
}

export interface ProfileSummary {
  id: number
  username: string
  display_name: string
}

export interface ProfileLookup extends ProfileSummary {
  email: string
}

export type SearchStatus = 'active' | 'completed' | 'archived'
export type SearchGender = 'female' | 'male' | 'mixed'
export type ParticipantRole = 'owner' | 'member'
export type InvitationStatus = 'pending' | 'accepted' | 'declined'
export type NameDecisionChoice = 'liked' | 'rejected' | 'skipped'

export interface FirstName {
  id: number
  name: string
  gender: SearchGender
  gender_label: string
  origin: string
  meaning: string
}

export interface NameSearchParticipant {
  id: number
  profile: ProfileSummary
  role: ParticipantRole
  role_label: string
  invitation_status: InvitationStatus
  invitation_status_label: string
  created_at: string
  updated_at: string
}

export interface InvitationSearchSummary {
  id: number
  title: string
  status: SearchStatus
  creator: ProfileSummary
}

export interface SearchInvitation {
  id: number
  search: InvitationSearchSummary
  profile: ProfileSummary
  role: ParticipantRole
  role_label: string
  invitation_status: InvitationStatus
  invitation_status_label: string
  created_at: string
  updated_at: string
}

export interface NameSearch {
  id: number
  title: string
  genders: SearchGender[]
  status: SearchStatus
  status_label: string
  creator: ProfileSummary
  participants: NameSearchParticipant[]
  created_at: string
  updated_at: string
}