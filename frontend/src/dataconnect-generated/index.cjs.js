const { queryRef, executeQuery, validateArgsWithOptions, mutationRef, executeMutation, validateArgs } = require('firebase/data-connect');

const connectorConfig = {
  connector: 'web',
  service: 'viral-content',
  location: 'us-central1'
};
exports.connectorConfig = connectorConfig;

const listDraftsRef = (dc) => {
  const { dc: dcInstance} = validateArgs(connectorConfig, dc, undefined);
  dcInstance._useGeneratedSdk();
  return queryRef(dcInstance, 'ListDrafts');
}
listDraftsRef.operationName = 'ListDrafts';
exports.listDraftsRef = listDraftsRef;

exports.listDrafts = function listDrafts(dcOrOptions, options) {
  
  const { dc: dcInstance, vars: inputVars, options: inputOpts } = validateArgsWithOptions(connectorConfig, dcOrOptions, options, undefined,false, false);
  return executeQuery(listDraftsRef(dcInstance, inputVars), inputOpts && { fetchPolicy: inputOpts.fetchPolicy });
}
;

const createDraftRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'CreateDraft', inputVars);
}
createDraftRef.operationName = 'CreateDraft';
exports.createDraftRef = createDraftRef;

exports.createDraft = function createDraft(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(createDraftRef(dcInstance, inputVars));
}
;

const deleteDraftRef = (dcOrVars, vars) => {
  const { dc: dcInstance, vars: inputVars} = validateArgs(connectorConfig, dcOrVars, vars, true);
  dcInstance._useGeneratedSdk();
  return mutationRef(dcInstance, 'DeleteDraft', inputVars);
}
deleteDraftRef.operationName = 'DeleteDraft';
exports.deleteDraftRef = deleteDraftRef;

exports.deleteDraft = function deleteDraft(dcOrVars, vars) {
  const { dc: dcInstance, vars: inputVars } = validateArgs(connectorConfig, dcOrVars, vars, true);
  return executeMutation(deleteDraftRef(dcInstance, inputVars));
}
;
