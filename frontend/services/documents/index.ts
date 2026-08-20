import { databricksSearchableChunks, listDatabricksDocuments, saveDatabricksDocument } from "./DatabricksDocumentRepository";
import { listDocuments as listLocalDocuments, saveDocument as saveLocalDocument, searchableChunks as localSearchableChunks } from "./repository";

export const listDocuments = () => process.env.DOCUMENT_MODE === "databricks" ? listDatabricksDocuments() : listLocalDocuments();
export const searchableChunks = (includeHR: boolean) => process.env.DOCUMENT_MODE === "databricks" ? databricksSearchableChunks(includeHR) : localSearchableChunks(includeHR);
export const saveDocument = (...args: Parameters<typeof saveLocalDocument>) => process.env.DOCUMENT_MODE === "databricks" ? saveDatabricksDocument(...args) : saveLocalDocument(...args);
