import { ConnectorConfig, DataConnect, QueryRef, QueryPromise, ExecuteQueryOptions, MutationRef, MutationPromise } from 'firebase/data-connect';

export const connectorConfig: ConnectorConfig;

export type TimestampString = string;
export type UUIDString = string;
export type Int64String = string;
export type DateString = string;




export interface CreateDraftData {
  draft_insert: Draft_Key;
}

export interface CreateDraftVariables {
  title: string;
  topic: string;
  platform: string;
  tone: string;
  caption: string;
  hashtags: string[];
}

export interface DeleteDraftData {
  draft_delete?: Draft_Key | null;
}

export interface DeleteDraftVariables {
  id: UUIDString;
}

export interface Draft_Key {
  id: UUIDString;
  __typename?: 'Draft_Key';
}

export interface ListDraftsData {
  drafts: ({
    id: UUIDString;
    title: string;
    topic: string;
    platform: string;
    tone: string;
    caption: string;
    hashtags: string[];
    createdAt: TimestampString;
    updatedAt: TimestampString;
  } & Draft_Key)[];
}

interface ListDraftsRef {
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<ListDraftsData, undefined>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect): QueryRef<ListDraftsData, undefined>;
  operationName: string;
}
export const listDraftsRef: ListDraftsRef;

export function listDrafts(options?: ExecuteQueryOptions): QueryPromise<ListDraftsData, undefined>;
export function listDrafts(dc: DataConnect, options?: ExecuteQueryOptions): QueryPromise<ListDraftsData, undefined>;

interface CreateDraftRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateDraftVariables): MutationRef<CreateDraftData, CreateDraftVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: CreateDraftVariables): MutationRef<CreateDraftData, CreateDraftVariables>;
  operationName: string;
}
export const createDraftRef: CreateDraftRef;

export function createDraft(vars: CreateDraftVariables): MutationPromise<CreateDraftData, CreateDraftVariables>;
export function createDraft(dc: DataConnect, vars: CreateDraftVariables): MutationPromise<CreateDraftData, CreateDraftVariables>;

interface DeleteDraftRef {
  /* Allow users to create refs without passing in DataConnect */
  (vars: DeleteDraftVariables): MutationRef<DeleteDraftData, DeleteDraftVariables>;
  /* Allow users to pass in custom DataConnect instances */
  (dc: DataConnect, vars: DeleteDraftVariables): MutationRef<DeleteDraftData, DeleteDraftVariables>;
  operationName: string;
}
export const deleteDraftRef: DeleteDraftRef;

export function deleteDraft(vars: DeleteDraftVariables): MutationPromise<DeleteDraftData, DeleteDraftVariables>;
export function deleteDraft(dc: DataConnect, vars: DeleteDraftVariables): MutationPromise<DeleteDraftData, DeleteDraftVariables>;

