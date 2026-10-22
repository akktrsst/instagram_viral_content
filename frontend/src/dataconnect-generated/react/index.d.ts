import { ListDraftsData, CreateDraftData, CreateDraftVariables, DeleteDraftData, DeleteDraftVariables } from '../';
import { UseDataConnectQueryResult, useDataConnectQueryOptions, UseDataConnectMutationResult, useDataConnectMutationOptions} from '@tanstack-query-firebase/react/data-connect';
import { UseQueryResult, UseMutationResult} from '@tanstack/react-query';
import { DataConnect } from 'firebase/data-connect';
import { FirebaseError } from 'firebase/app';


export function useListDrafts(options?: useDataConnectQueryOptions<ListDraftsData>): UseDataConnectQueryResult<ListDraftsData, undefined>;
export function useListDrafts(dc: DataConnect, options?: useDataConnectQueryOptions<ListDraftsData>): UseDataConnectQueryResult<ListDraftsData, undefined>;

export function useCreateDraft(options?: useDataConnectMutationOptions<CreateDraftData, FirebaseError, CreateDraftVariables>): UseDataConnectMutationResult<CreateDraftData, CreateDraftVariables>;
export function useCreateDraft(dc: DataConnect, options?: useDataConnectMutationOptions<CreateDraftData, FirebaseError, CreateDraftVariables>): UseDataConnectMutationResult<CreateDraftData, CreateDraftVariables>;

export function useDeleteDraft(options?: useDataConnectMutationOptions<DeleteDraftData, FirebaseError, DeleteDraftVariables>): UseDataConnectMutationResult<DeleteDraftData, DeleteDraftVariables>;
export function useDeleteDraft(dc: DataConnect, options?: useDataConnectMutationOptions<DeleteDraftData, FirebaseError, DeleteDraftVariables>): UseDataConnectMutationResult<DeleteDraftData, DeleteDraftVariables>;
