# Generated TypeScript README
This README will guide you through the process of using the generated JavaScript SDK package for the connector `web`. It will also provide examples on how to use your generated SDK to call your Data Connect queries and mutations.

**If you're looking for the `React README`, you can find it at [`dataconnect-generated/react/README.md`](./react/README.md)**

***NOTE:** This README is generated alongside the generated SDK. If you make changes to this file, they will be overwritten when the SDK is regenerated.*

# Table of Contents
- [**Overview**](#generated-javascript-readme)
- [**Accessing the connector**](#accessing-the-connector)
  - [*Connecting to the local Emulator*](#connecting-to-the-local-emulator)
- [**Queries**](#queries)
  - [*ListDrafts*](#listdrafts)
- [**Mutations**](#mutations)
  - [*CreateDraft*](#createdraft)
  - [*DeleteDraft*](#deletedraft)

# Accessing the connector
A connector is a collection of Queries and Mutations. One SDK is generated for each connector - this SDK is generated for the connector `web`. You can find more information about connectors in the [Data Connect documentation](https://firebase.google.com/docs/data-connect#how-does).

You can use this generated SDK by importing from the package `@dataconnect/generated` as shown below. Both CommonJS and ESM imports are supported.

You can also follow the instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#set-client).

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@dataconnect/generated';

const dataConnect = getDataConnect(connectorConfig);
```

## Connecting to the local Emulator
By default, the connector will connect to the production service.

To connect to the emulator, you can use the following code.
You can also follow the emulator instructions from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#instrument-clients).

```typescript
import { connectDataConnectEmulator, getDataConnect } from 'firebase/data-connect';
import { connectorConfig } from '@dataconnect/generated';

const dataConnect = getDataConnect(connectorConfig);
connectDataConnectEmulator(dataConnect, 'localhost', 9399);
```

After it's initialized, you can call your Data Connect [queries](#queries) and [mutations](#mutations) from your generated SDK.

# Queries

There are two ways to execute a Data Connect Query using the generated Web SDK:
- Using a Query Reference function, which returns a `QueryRef`
  - The `QueryRef` can be used as an argument to `executeQuery()`, which will execute the Query and return a `QueryPromise`
- Using an action shortcut function, which returns a `QueryPromise`
  - Calling the action shortcut function will execute the Query and return a `QueryPromise`

The following is true for both the action shortcut function and the `QueryRef` function:
- The `QueryPromise` returned will resolve to the result of the Query once it has finished executing
- If the Query accepts arguments, both the action shortcut function and the `QueryRef` function accept a single argument: an object that contains all the required variables (and the optional variables) for the Query
- Both functions can be called with or without passing in a `DataConnect` instance as an argument. If no `DataConnect` argument is passed in, then the generated SDK will call `getDataConnect(connectorConfig)` behind the scenes for you.

Below are examples of how to use the `web` connector's generated functions to execute each query. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-queries).

## ListDrafts
You can execute the `ListDrafts` query using the following action shortcut function, or by calling `executeQuery()` after calling the following `QueryRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
listDrafts(options?: ExecuteQueryOptions): QueryPromise<ListDraftsData, undefined>;

interface ListDraftsRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (): QueryRef<ListDraftsData, undefined>;
}
export const listDraftsRef: ListDraftsRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `QueryRef` function.
```typescript
listDrafts(dc: DataConnect, options?: ExecuteQueryOptions): QueryPromise<ListDraftsData, undefined>;

interface ListDraftsRef {
  ...
  (dc: DataConnect): QueryRef<ListDraftsData, undefined>;
}
export const listDraftsRef: ListDraftsRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the listDraftsRef:
```typescript
const name = listDraftsRef.operationName;
console.log(name);
```

### Variables
The `ListDrafts` query has no variables.
### Return Type
Recall that executing the `ListDrafts` query returns a `QueryPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `ListDraftsData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
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
```
### Using `ListDrafts`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, listDrafts } from '@dataconnect/generated';


// Call the `listDrafts()` function to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await listDrafts();

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await listDrafts(dataConnect);

console.log(data.drafts);

// Or, you can use the `Promise` API.
listDrafts().then((response) => {
  const data = response.data;
  console.log(data.drafts);
});
```

### Using `ListDrafts`'s `QueryRef` function

```typescript
import { getDataConnect, executeQuery } from 'firebase/data-connect';
import { connectorConfig, listDraftsRef } from '@dataconnect/generated';


// Call the `listDraftsRef()` function to get a reference to the query.
const ref = listDraftsRef();

// You can also pass in a `DataConnect` instance to the `QueryRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = listDraftsRef(dataConnect);

// Call `executeQuery()` on the reference to execute the query.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeQuery(ref);

console.log(data.drafts);

// Or, you can use the `Promise` API.
executeQuery(ref).then((response) => {
  const data = response.data;
  console.log(data.drafts);
});
```

# Mutations

There are two ways to execute a Data Connect Mutation using the generated Web SDK:
- Using a Mutation Reference function, which returns a `MutationRef`
  - The `MutationRef` can be used as an argument to `executeMutation()`, which will execute the Mutation and return a `MutationPromise`
- Using an action shortcut function, which returns a `MutationPromise`
  - Calling the action shortcut function will execute the Mutation and return a `MutationPromise`

The following is true for both the action shortcut function and the `MutationRef` function:
- The `MutationPromise` returned will resolve to the result of the Mutation once it has finished executing
- If the Mutation accepts arguments, both the action shortcut function and the `MutationRef` function accept a single argument: an object that contains all the required variables (and the optional variables) for the Mutation
- Both functions can be called with or without passing in a `DataConnect` instance as an argument. If no `DataConnect` argument is passed in, then the generated SDK will call `getDataConnect(connectorConfig)` behind the scenes for you.

Below are examples of how to use the `web` connector's generated functions to execute each mutation. You can also follow the examples from the [Data Connect documentation](https://firebase.google.com/docs/data-connect/web-sdk#using-mutations).

## CreateDraft
You can execute the `CreateDraft` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
createDraft(vars: CreateDraftVariables): MutationPromise<CreateDraftData, CreateDraftVariables>;

interface CreateDraftRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: CreateDraftVariables): MutationRef<CreateDraftData, CreateDraftVariables>;
}
export const createDraftRef: CreateDraftRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
createDraft(dc: DataConnect, vars: CreateDraftVariables): MutationPromise<CreateDraftData, CreateDraftVariables>;

interface CreateDraftRef {
  ...
  (dc: DataConnect, vars: CreateDraftVariables): MutationRef<CreateDraftData, CreateDraftVariables>;
}
export const createDraftRef: CreateDraftRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the createDraftRef:
```typescript
const name = createDraftRef.operationName;
console.log(name);
```

### Variables
The `CreateDraft` mutation requires an argument of type `CreateDraftVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface CreateDraftVariables {
  title: string;
  topic: string;
  platform: string;
  tone: string;
  caption: string;
  hashtags: string[];
}
```
### Return Type
Recall that executing the `CreateDraft` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `CreateDraftData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface CreateDraftData {
  draft_insert: Draft_Key;
}
```
### Using `CreateDraft`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, createDraft, CreateDraftVariables } from '@dataconnect/generated';

// The `CreateDraft` mutation requires an argument of type `CreateDraftVariables`:
const createDraftVars: CreateDraftVariables = {
  title: ..., 
  topic: ..., 
  platform: ..., 
  tone: ..., 
  caption: ..., 
  hashtags: ..., 
};

// Call the `createDraft()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await createDraft(createDraftVars);
// Variables can be defined inline as well.
const { data } = await createDraft({ title: ..., topic: ..., platform: ..., tone: ..., caption: ..., hashtags: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await createDraft(dataConnect, createDraftVars);

console.log(data.draft_insert);

// Or, you can use the `Promise` API.
createDraft(createDraftVars).then((response) => {
  const data = response.data;
  console.log(data.draft_insert);
});
```

### Using `CreateDraft`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, createDraftRef, CreateDraftVariables } from '@dataconnect/generated';

// The `CreateDraft` mutation requires an argument of type `CreateDraftVariables`:
const createDraftVars: CreateDraftVariables = {
  title: ..., 
  topic: ..., 
  platform: ..., 
  tone: ..., 
  caption: ..., 
  hashtags: ..., 
};

// Call the `createDraftRef()` function to get a reference to the mutation.
const ref = createDraftRef(createDraftVars);
// Variables can be defined inline as well.
const ref = createDraftRef({ title: ..., topic: ..., platform: ..., tone: ..., caption: ..., hashtags: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = createDraftRef(dataConnect, createDraftVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.draft_insert);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.draft_insert);
});
```

## DeleteDraft
You can execute the `DeleteDraft` mutation using the following action shortcut function, or by calling `executeMutation()` after calling the following `MutationRef` function, both of which are defined in [dataconnect-generated/index.d.ts](./index.d.ts):
```typescript
deleteDraft(vars: DeleteDraftVariables): MutationPromise<DeleteDraftData, DeleteDraftVariables>;

interface DeleteDraftRef {
  ...
  /* Allow users to create refs without passing in DataConnect */
  (vars: DeleteDraftVariables): MutationRef<DeleteDraftData, DeleteDraftVariables>;
}
export const deleteDraftRef: DeleteDraftRef;
```
You can also pass in a `DataConnect` instance to the action shortcut function or `MutationRef` function.
```typescript
deleteDraft(dc: DataConnect, vars: DeleteDraftVariables): MutationPromise<DeleteDraftData, DeleteDraftVariables>;

interface DeleteDraftRef {
  ...
  (dc: DataConnect, vars: DeleteDraftVariables): MutationRef<DeleteDraftData, DeleteDraftVariables>;
}
export const deleteDraftRef: DeleteDraftRef;
```

If you need the name of the operation without creating a ref, you can retrieve the operation name by calling the `operationName` property on the deleteDraftRef:
```typescript
const name = deleteDraftRef.operationName;
console.log(name);
```

### Variables
The `DeleteDraft` mutation requires an argument of type `DeleteDraftVariables`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:

```typescript
export interface DeleteDraftVariables {
  id: UUIDString;
}
```
### Return Type
Recall that executing the `DeleteDraft` mutation returns a `MutationPromise` that resolves to an object with a `data` property.

The `data` property is an object of type `DeleteDraftData`, which is defined in [dataconnect-generated/index.d.ts](./index.d.ts). It has the following fields:
```typescript
export interface DeleteDraftData {
  draft_delete?: Draft_Key | null;
}
```
### Using `DeleteDraft`'s action shortcut function

```typescript
import { getDataConnect } from 'firebase/data-connect';
import { connectorConfig, deleteDraft, DeleteDraftVariables } from '@dataconnect/generated';

// The `DeleteDraft` mutation requires an argument of type `DeleteDraftVariables`:
const deleteDraftVars: DeleteDraftVariables = {
  id: ..., 
};

// Call the `deleteDraft()` function to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await deleteDraft(deleteDraftVars);
// Variables can be defined inline as well.
const { data } = await deleteDraft({ id: ..., });

// You can also pass in a `DataConnect` instance to the action shortcut function.
const dataConnect = getDataConnect(connectorConfig);
const { data } = await deleteDraft(dataConnect, deleteDraftVars);

console.log(data.draft_delete);

// Or, you can use the `Promise` API.
deleteDraft(deleteDraftVars).then((response) => {
  const data = response.data;
  console.log(data.draft_delete);
});
```

### Using `DeleteDraft`'s `MutationRef` function

```typescript
import { getDataConnect, executeMutation } from 'firebase/data-connect';
import { connectorConfig, deleteDraftRef, DeleteDraftVariables } from '@dataconnect/generated';

// The `DeleteDraft` mutation requires an argument of type `DeleteDraftVariables`:
const deleteDraftVars: DeleteDraftVariables = {
  id: ..., 
};

// Call the `deleteDraftRef()` function to get a reference to the mutation.
const ref = deleteDraftRef(deleteDraftVars);
// Variables can be defined inline as well.
const ref = deleteDraftRef({ id: ..., });

// You can also pass in a `DataConnect` instance to the `MutationRef` function.
const dataConnect = getDataConnect(connectorConfig);
const ref = deleteDraftRef(dataConnect, deleteDraftVars);

// Call `executeMutation()` on the reference to execute the mutation.
// You can use the `await` keyword to wait for the promise to resolve.
const { data } = await executeMutation(ref);

console.log(data.draft_delete);

// Or, you can use the `Promise` API.
executeMutation(ref).then((response) => {
  const data = response.data;
  console.log(data.draft_delete);
});
```

