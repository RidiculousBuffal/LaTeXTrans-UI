import { useMemo, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { z } from "zod"
import { FileArchiveIcon, GlobeIcon, Loader2Icon, UploadIcon } from "lucide-react"

import { createArxivTask, createUploadTask } from "@/lib/api"
import { queryClient } from "@/lib/query-client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldSeparator,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { getErrorMessage } from "@/lib/utils-format"

const commonSchema = {
  task_name: z.string().min(2, "Task name is required."),
  source_language: z.string().min(1, "Source language is required."),
  target_language: z.string().min(1, "Target language is required."),
  model_name: z.string().min(1, "Model name is required."),
  created_by: z.string().min(1, "Creator is required."),
  env_profile: z.string().min(1, "Environment profile is required."),
  output_name: z.string().min(1, "Output name is required."),
  mode: z.string().min(1, "Mode is required."),
  update_term: z.enum(["False", "True"]),
  user_term: z.string(),
}

const arxivSchema = z.object({
  ...commonSchema,
  arxiv_id: z.string().min(3, "arXiv ID is required."),
})

const uploadSchema = z.object({
  ...commonSchema,
  file: z.instanceof(File, { message: "Archive file is required." }),
})

type ArxivFormValues = z.infer<typeof arxivSchema>
type UploadFormValues = z.infer<typeof uploadSchema>

const defaultValues = {
  task_name: "",
  source_language: "en",
  target_language: "zh",
  model_name: "gpt-5.4",
  created_by: "frontend-user",
  env_profile: "default",
  output_name: "",
  mode: "0",
  update_term: "False" as const,
  user_term: "",
}

type SharedFieldName = keyof typeof defaultValues

export function NewTaskPage() {
  const [tab, setTab] = useState("arxiv")
  const navigate = useNavigate()

  const arxivForm = useForm<ArxivFormValues>({
    resolver: zodResolver(arxivSchema),
    defaultValues: {
      ...defaultValues,
      arxiv_id: "",
    },
  })

  const uploadForm = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      ...defaultValues,
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

  const isSubmitting = arxivMutation.isPending || uploadMutation.isPending

  const sharedTip = useMemo(
    () =>
      "MVP currently submits directly to the FastAPI backend. If a field is optional in the API, we still expose it here so tasks are reproducible.",
    []
  )

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <Card>
        <CardHeader>
          <CardTitle>Create a translation task</CardTitle>
          <CardDescription>
            Start from an arXiv paper ID or upload a source archive. Both flows map directly to the backend API reference.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="arxiv">
                <GlobeIcon data-icon="inline-start" />
                arXiv task
              </TabsTrigger>
              <TabsTrigger value="upload">
                <UploadIcon data-icon="inline-start" />
                Upload task
              </TabsTrigger>
            </TabsList>

            <TabsContent value="arxiv" className="pt-5">
              <form
                className="flex flex-col gap-5"
                onSubmit={arxivForm.handleSubmit((values) => {
                  arxivMutation.mutate({
                    task_name: values.task_name,
                    source_type: "arxiv",
                    arxiv_id: values.arxiv_id,
                    source_language: values.source_language,
                    target_language: values.target_language,
                    model_name: values.model_name,
                    created_by: values.created_by,
                    env_profile: values.env_profile,
                    output_name: values.output_name,
                    options: {
                      mode: values.mode,
                      update_term: values.update_term,
                      user_term: values.user_term,
                    },
                  })
                })}
              >
                <TaskFormFields
                  modeControl={
                    <Field>
                      <FieldLabel htmlFor="arxiv-id">arXiv ID</FieldLabel>
                      <FieldContent>
                        <Input id="arxiv-id" placeholder="2501.00001" {...arxivForm.register("arxiv_id")} />
                        <FieldError errors={[arxivForm.formState.errors.arxiv_id]} />
                      </FieldContent>
                    </Field>
                  }
                  registerField={(name) => arxivForm.register(name)}
                  values={{
                    task_name: arxivForm.watch("task_name"),
                    source_language: arxivForm.watch("source_language"),
                    target_language: arxivForm.watch("target_language"),
                    model_name: arxivForm.watch("model_name"),
                    created_by: arxivForm.watch("created_by"),
                    env_profile: arxivForm.watch("env_profile"),
                    output_name: arxivForm.watch("output_name"),
                    mode: arxivForm.watch("mode"),
                    update_term: arxivForm.watch("update_term"),
                    user_term: arxivForm.watch("user_term"),
                  }}
                  setFieldValue={(name, value) =>
                    arxivForm.setValue(name, value, { shouldValidate: true })
                  }
                  errors={arxivForm.formState.errors as SharedTaskFormErrors}
                  isSubmitting={isSubmitting}
                  submitLabel="Create arXiv task"
                />
              </form>
            </TabsContent>

            <TabsContent value="upload" className="pt-5">
              <form
                className="flex flex-col gap-5"
                onSubmit={uploadForm.handleSubmit((values) => {
                  uploadMutation.mutate({
                    file: values.file,
                    task_name: values.task_name,
                    source_language: values.source_language,
                    target_language: values.target_language,
                    model_name: values.model_name,
                    created_by: values.created_by,
                    env_profile: values.env_profile,
                    output_name: values.output_name,
                    options: {
                      mode: values.mode,
                      update_term: values.update_term,
                      user_term: values.user_term,
                    },
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
                          if (!uploadForm.getValues("task_name")) {
                            uploadForm.setValue("task_name", file.name.replace(/\.(zip|tar|tar\.gz|tgz)$/i, ""))
                          }
                        }
                      }}
                    />
                    <FieldDescription>
                      Supported archive formats: `.zip`, `.tar`, `.tar.gz`, `.tgz`
                    </FieldDescription>
                    <FieldError errors={[uploadForm.formState.errors.file]} />
                  </FieldContent>
                </Field>

                <TaskFormFields
                  registerField={(name) => uploadForm.register(name)}
                  values={{
                    task_name: uploadForm.watch("task_name"),
                    source_language: uploadForm.watch("source_language"),
                    target_language: uploadForm.watch("target_language"),
                    model_name: uploadForm.watch("model_name"),
                    created_by: uploadForm.watch("created_by"),
                    env_profile: uploadForm.watch("env_profile"),
                    output_name: uploadForm.watch("output_name"),
                    mode: uploadForm.watch("mode"),
                    update_term: uploadForm.watch("update_term"),
                    user_term: uploadForm.watch("user_term"),
                  }}
                  setFieldValue={(name, value) =>
                    uploadForm.setValue(name, value, { shouldValidate: true })
                  }
                  errors={uploadForm.formState.errors as SharedTaskFormErrors}
                  isSubmitting={isSubmitting}
                  submitLabel="Create upload task"
                />
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-6">
        <Alert>
          <FileArchiveIcon />
          <AlertTitle>Submission tips</AlertTitle>
          <AlertDescription>{sharedTip}</AlertDescription>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>Backend mapping</CardTitle>
            <CardDescription>Fields shown here map to the current backend contract.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
            <p>`POST /api/tasks` for arXiv submissions.</p>
            <p>`POST /api/tasks/upload` for archive uploads.</p>
            <p>`options` is serialized as JSON for uploads, matching the API reference.</p>
            <p>Successful submission returns a `TaskDetailResponse`, then we navigate straight to the detail page.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

type SharedTaskFormErrors = Partial<Record<SharedFieldName, { message?: string } | undefined>>

function TaskFormFields({
  modeControl,
  registerField,
  setFieldValue,
  values,
  errors,
  isSubmitting,
  submitLabel,
}: {
  modeControl?: React.ReactNode
  registerField: (name: SharedFieldName) => Record<string, unknown>
  setFieldValue: (name: SharedFieldName, value: string) => void
  values: Record<SharedFieldName, string>
  errors: SharedTaskFormErrors
  isSubmitting: boolean
  submitLabel: string
}) {
  const selectedUpdateTerm = values.update_term as "False" | "True"

  return (
    <>
      {modeControl}
      <FieldGroup className="grid gap-4 md:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="task_name">Task name</FieldLabel>
          <FieldContent>
            <Input id="task_name" placeholder="paper-2501-00001" {...registerField("task_name")} />
            <FieldError errors={[errors.task_name]} />
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel htmlFor="output_name">Output name</FieldLabel>
          <FieldContent>
            <Input id="output_name" placeholder="paper-2501-00001-zh" {...registerField("output_name")} />
            <FieldError errors={[errors.output_name]} />
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel>Source language</FieldLabel>
          <FieldContent>
            <Select
              value={values.source_language}
              onValueChange={(value) => setFieldValue("source_language", value)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select source language" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh">Chinese</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel>Target language</FieldLabel>
          <FieldContent>
            <Select
              value={values.target_language}
              onValueChange={(value) => setFieldValue("target_language", value)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select target language" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="zh">Chinese</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel htmlFor="model_name">Model name</FieldLabel>
          <FieldContent>
            <Input id="model_name" placeholder="gpt-5.4" {...registerField("model_name")} />
            <FieldError errors={[errors.model_name]} />
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel htmlFor="created_by">Created by</FieldLabel>
          <FieldContent>
            <Input id="created_by" placeholder="frontend-user" {...registerField("created_by")} />
            <FieldError errors={[errors.created_by]} />
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel htmlFor="env_profile">Environment profile</FieldLabel>
          <FieldContent>
            <Input id="env_profile" placeholder="default" {...registerField("env_profile")} />
            <FieldError errors={[errors.env_profile]} />
          </FieldContent>
        </Field>
        <Field>
          <FieldLabel htmlFor="mode">Mode</FieldLabel>
          <FieldContent>
            <Input id="mode" placeholder="0" {...registerField("mode")} />
            <FieldDescription>Passed through to `options.mode`.</FieldDescription>
            <FieldError errors={[errors.mode]} />
          </FieldContent>
        </Field>
      </FieldGroup>

      <FieldSeparator>Term behavior</FieldSeparator>

      <Field>
        <FieldLabel>Update term</FieldLabel>
        <FieldContent>
          <ToggleGroup
            type="single"
            value={selectedUpdateTerm}
            onValueChange={(value) => {
              if (value === "False" || value === "True") {
                setFieldValue("update_term", value)
              }
            }}
          >
            <ToggleGroupItem value="False">False</ToggleGroupItem>
            <ToggleGroupItem value="True">True</ToggleGroupItem>
          </ToggleGroup>
          <FieldDescription>
            Matches the current backend examples, which use string values.
          </FieldDescription>
        </FieldContent>
      </Field>

      <Field>
        <FieldLabel htmlFor="user_term">User term hints</FieldLabel>
        <FieldContent>
          <Textarea
            id="user_term"
            placeholder="Optional glossary or translation hints."
            {...registerField("user_term")}
          />
          <FieldDescription>
            Sent as `options.user_term`.
          </FieldDescription>
        </FieldContent>
      </Field>

      <div className="flex justify-end">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2Icon className="animate-spin" data-icon="inline-start" />}
          {submitLabel}
        </Button>
      </div>
    </>
  )
}
