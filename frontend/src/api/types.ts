import z from 'zod'

// ── Column metadata ───────────────────────────────────────────────────────────
export const ColumnInfoSchema = z.object({
  name: z.string(),
  dtype: z.enum(['numeric', 'categorical', 'datetime', 'text']),
  missing_count: z.number(),
})
export type ColumnInfo = z.infer<typeof ColumnInfoSchema>

// ── File upload response ──────────────────────────────────────────────────────
export const FileUploadResponseSchema = z.object({
  file_id: z.string(),
  status: z.enum(['validated', 'needs_sheet_selection', 'error']),
  row_count: z.number().nullable().optional(),
  columns: z.array(ColumnInfoSchema).nullable().optional(),
  preview_rows: z.array(z.record(z.unknown())).nullable().optional(),
  // sheet_names is empty for CSVs and single-sheet Excels.
  // We parse null/undefined safely and default to an empty array.
  sheet_names: z.array(z.string()).nullable().optional().transform(val => val ?? []),
})
export type FileUploadResponse = z.infer<typeof FileUploadResponseSchema>

// ── File Data response ────────────────────────────────────────────────────────
export const FileDataResponseSchema = z.object({
  data: z.array(z.record(z.unknown())),
  is_truncated: z.boolean(),
  total_rows: z.number(),
})
export type FileDataResponse = z.infer<typeof FileDataResponseSchema>

// ── Chart ─────────────────────────────────────────────────────────────────────
export const ChartPayloadSchema = z.object({
  chart_id: z.string(),
  chart_type: z.enum(['bar', 'line', 'area', 'pie', 'scatter', 'histogram', 'heatmap']),
  chart_spec: z.record(z.unknown()),
})
export type ChartPayload = z.infer<typeof ChartPayloadSchema>

// ── Prompt response ───────────────────────────────────────────────────────────
export const PromptResponseSchema = z.object({
  prompt_id: z.string(),
  status: z.enum(['pending', 'processing', 'awaiting_clarification', 'completed', 'failed']),
  chart: ChartPayloadSchema.optional(),
  clarification_question: z.string().optional(),
  error_message: z.string().optional(),
})
export type PromptResponse = z.infer<typeof PromptResponseSchema>

// ── WebSocket event ───────────────────────────────────────────────────────────
export type WsEvent =
  | { status: 'pending'; message: string }
  | { status: 'processing'; message: string }
  | { status: 'awaiting_clarification'; clarification_question: string }
  | { status: 'completed'; chart: ChartPayload; explanation?: string | null }
  | { status: 'failed'; message: string }
