interface D1Result<T = unknown> { results?: T[]; success: boolean; meta?: unknown }
interface D1PreparedStatement { bind(...values: unknown[]): D1PreparedStatement; run<T = unknown>(): Promise<D1Result<T>>; all<T = unknown>(): Promise<D1Result<T>>; first<T = unknown>(): Promise<T | null> }
interface D1Database { prepare(query: string): D1PreparedStatement; batch<T = unknown>(statements: D1PreparedStatement[]): Promise<D1Result<T>[]> }
interface R2Bucket { put(key: string, value: ArrayBuffer | ArrayBufferView | string | ReadableStream, options?: { httpMetadata?: { contentType?: string }; customMetadata?: Record<string, string> }): Promise<unknown> }
declare module "cloudflare:workers" { export const env: { DB?: D1Database; DOCS?: R2Bucket } }
