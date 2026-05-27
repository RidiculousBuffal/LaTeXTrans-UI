import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"
import { FileArchiveIcon, FileTextIcon, GlobeIcon, Loader2Icon, UploadIcon } from "lucide-react"

import { createArxivTask, createPdfTask, createUploadTask } from "@/lib/api"
import { queryClient } from "@/lib/query-client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { getErrorMessage } from "@/lib/utils-format"

const arxivSchema = z.object({
  arxiv_id: z.string().min(3, "arXiv ID is required."),
})

const uploadSchema = z.object({
  file: z.instanceof(File, { message: "Archive file is required." }),
})

const pdfSchema = z.object({
  file: z.instanceof(File, { message: "PDF file is required." }),
})

type ArxivFormValues = z.infer<typeof arxivSchema>
type UploadFormValues = z.infer<typeof uploadSchema>
type PdfFormValues = z.infer<typeof pdfSchema>

export function NewTaskPage() {
  const [tab, setTab] = useState("arxiv")
  const navigate = useNavigate()

  const arxivForm = useForm<ArxivFormValues>({
    resolver: zodResolver(arxivSchema),
    defaultValues: {
      arxiv_id: "",
    },
  })

  const uploadForm = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      file: undefined as unknown as File,
    },
  })

  const pdfForm = useForm<PdfFormValues>({
    resolver: zodResolver(pdfSchema),
    defaultValues: {
      file: undefined as unknown as File,
    },
  })

  const arxivMutation = useMutation({
    mutationFn: createArxivTask,
    onSuccess: (task) => {
      toast.success("Task created", {
        description: `Task ${task.task_name} is now queued.`,
      })
      void queryClient.invalidateQueries({ queryKey: ["tasks"] })
      navigate(`/tasks/${task.id}`)
    },
    onError: (error) => {
      toast.error("Task creation failed", {
        description: getErrorMessage(error),
      })
    },
  })

  const uploadMutation = useMutation({
    mutationFn: createUploadTask,
    onSuccess: (task) => {
      toast.success("Upload task created", {
        description: `Task ${task.task_name} is now queued.`,
      })
      void queryClient.invalidateQueries({ queryKey: ["tasks"] })
      navigate(`/tasks/${task.id}`)
    },
    onError: (error) => {
      toast.error("Upload task failed", {
        description: getErrorMessage(error),
      })
    },
  })

  const pdfMutation = useMutation({
    mutationFn: createPdfTask,
    onSuccess: (task) => {
      toast.success("PDF task created", {
        description: `Task ${task.task_name} is now queued.`,
      })
      void queryClient.invalidateQueries({ queryKey: ["tasks"] })
      navigate(`/tasks/${task.id}`)
    },
    onError: (error) => {
      toast.error("PDF task failed", {
        description: getErrorMessage(error),
      })
    },
  })

  const isSubmitting = arxivMutation.isPending || uploadMutation.isPending || pdfMutation.isPending

  return (
    <div className="mx-auto grid w-full max-w-3xl gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Create a translation task</CardTitle>
          <CardDescription>
            Submit the source only. The backend fills in task names, languages, model settings, and runtime options.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="arxiv">
                <GlobeIcon data-icon="inline-start" />
                arXiv
              </TabsTrigger>
              <TabsTrigger value="upload">
                <UploadIcon data-icon="inline-start" />
                Upload
              </TabsTrigger>
              <TabsTrigger value="pdf">
                <FileTextIcon data-icon="inline-start" />
                PDF
              </TabsTrigger>
            </TabsList>

            <TabsContent value="arxiv" className="pt-5">
              <form
                className="flex flex-col gap-5"
                onSubmit={arxivForm.handleSubmit((values) => {
                  arxivMutation.mutate({
                    source_type: "arxiv",
                    arxiv_id: values.arxiv_id.trim(),
                  })
                })}
              >
                <Field>
                  <FieldLabel htmlFor="arxiv-id">arXiv ID</FieldLabel>
                  <FieldContent>
                    <Input
                      id="arxiv-id"
                      autoComplete="off"
                      placeholder="2605.23618"
                      {...arxivForm.register("arxiv_id")}
                    />
                    <FieldDescription>
                      Task metadata and translation options will use backend defaults.
                    </FieldDescription>
                    <FieldError errors={[arxivForm.formState.errors.arxiv_id]} />
                  </FieldContent>
                </Field>

                <div className="flex justify-end">
                  <Button type="submit" disabled={isSubmitting}>
                    {arxivMutation.isPending && (
                      <Loader2Icon className="animate-spin" data-icon="inline-start" />
                    )}
                    Create task
                  </Button>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="upload" className="pt-5">
              <form
                className="flex flex-col gap-5"
                onSubmit={uploadForm.handleSubmit((values) => {
                  uploadMutation.mutate({
                    file: values.file,
                  })
                })}
              >
                <Field>
                  <FieldLabel htmlFor="source-file">Source archive</FieldLabel>
                  <FieldContent>
                    <Input
                      id="source-file"
                      type="file"
                      accept=".zip,.tar,.tar.gz,.tgz"
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (file) {
                          uploadForm.setValue("file", file, { shouldValidate: true })
                        }
                      }}
                    />
                    <FieldDescription>
                      Supported archive formats: .zip, .tar, .tar.gz, .tgz.
                    </FieldDescription>
                    <FieldError errors={[uploadForm.formState.errors.file]} />
                  </FieldContent>
                </Field>

                <div className="flex justify-end">
                  <Button type="submit" disabled={isSubmitting}>
                    {uploadMutation.isPending && (
                      <Loader2Icon className="animate-spin" data-icon="inline-start" />
                    )}
                    Upload and create task
                  </Button>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="pdf" className="pt-5">
              <form
                className="flex flex-col gap-5"
                onSubmit={pdfForm.handleSubmit((values) => {
                  pdfMutation.mutate({
                    file: values.file,
                  })
                })}
              >
                <Field>
                  <FieldLabel htmlFor="pdf-file">PDF file</FieldLabel>
                  <FieldContent>
                    <Input
                      id="pdf-file"
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (file) {
                          pdfForm.setValue("file", file, { shouldValidate: true })
                        }
                      }}
                    />
                    <FieldDescription>
                      Upload a PDF and run it through BabelDOC with backend defaults.
                    </FieldDescription>
                    <FieldError errors={[pdfForm.formState.errors.file]} />
                  </FieldContent>
                </Field>

                <div className="flex justify-end">
                  <Button type="submit" disabled={isSubmitting}>
                    {pdfMutation.isPending && (
                      <Loader2Icon className="animate-spin" data-icon="inline-start" />
                    )}
                    Upload PDF and create task
                  </Button>
                </div>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
        <FileArchiveIcon className="mt-0.5 size-4 shrink-0" />
        <p>
          Task name, owner, model, language, output name, and options are resolved by the backend.
        </p>
      </div>
    </div>
  )
}
