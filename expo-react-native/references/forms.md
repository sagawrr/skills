# Forms — React Hook Form v7 + Zod v4

> Pinned: @hookform/resolvers · zod v4 · react-hook-form v7

---

## Setup

> **Zod v4 migration**: format validators are now top-level (`z.email()`, `z.url()`, `z.uuid()` — not method chains). `z.record` requires 2 args. `z.nativeEnum` → `z.enum`. Error params unified to `{ error }`. Full migration table in **Anti-Pattern Hard Stops** below.

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Zod v4 — format validators are top-level
const LoginSchema = z.object({
  email:    z.email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters'),
});

// Always z.infer — never write a separate interface
type LoginForm = z.infer<typeof LoginSchema>;

const { control, handleSubmit, formState, reset } = useForm<LoginForm>({
  resolver: zodResolver(LoginSchema),
  defaultValues: { email: '', password: '' }, // always concrete — never undefined
  mode: 'onBlur',         // NOT onChange — explicit perf warning in RHF docs
  reValidateMode: 'onChange',
});
```

---

## React Native: always `useController`

`register()` spreads DOM refs — doesn't work on RN `TextInput`. Use `useController` always.

```tsx
import { useController, Control } from 'react-hook-form';

function FormField({
  control,
  name,
  placeholder,
  secureTextEntry,
  keyboardType,
}: {
  control: Control<any>;
  name: string;
  placeholder?: string;
  secureTextEntry?: boolean;
  keyboardType?: TextInputProps['keyboardType'];
}) {
  const { field, fieldState: { error } } = useController({ control, name });
  return (
    <>
      <TextInput
        value={String(field.value ?? '')}
        onChangeText={field.onChange}
        onBlur={field.onBlur}
        placeholder={placeholder}
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
      />
      {error && <Text style={s.error}>{error.message}</Text>}
    </>
  );
}
```

---

## formState Proxy — The Subscription Trap

`formState` is a JS Proxy. A sub-property subscription **only activates when the getter is called**. Conditional access silently breaks reactivity.

```tsx
// ❌ short-circuit skips isValid getter — no subscription
const isDisabled = !formState.isDirty || !formState.isValid;

// ❌ Proxy fires once at declaration — effect never re-runs on error changes
useEffect(() => { log(errors); }, [formState.errors]);

// ✅ destructure unconditionally at the top of the component
const { isDirty, isValid, errors } = formState;
const isDisabled = !isDirty || !isValid;
useEffect(() => { log(errors); }, [formState]); // depend on formState, not sub-property
```

---

## `watch` vs `useWatch` vs `getValues`

| API | Re-renders | Use for |
|-----|-----------|---------|
| `watch('f')` | Entire form tree | Avoid — use `useWatch` |
| `useWatch({ control, name })` | Calling component only | Reactive UI (show/hide, dependent fields) |
| `getValues('f')` | Never | Callbacks, `onSubmit`, analytics |

```tsx
// ✅ isolated re-render
const country = useWatch({ control, name: 'country' });

// ✅ non-reactive read in callback
const onConfirm = () => analytics.track('confirmed', getValues());
```

---

## `defaultValues` — Caching Rules

```tsx
// ❌ undefined breaks controlled component state
useForm({ defaultValues: { name: undefined } });

// ❌ re-passing values to useForm after mount — has NO effect
useForm({ defaultValues: newUser });

// ✅ async defaultValues — RHF sets formState.isLoading=true, resolves Promise, then resets
// No React Suspense involved — check formState.isLoading to gate render
useForm({ defaultValues: async () => fetchUser(id) });

// ✅ update after mount — reset() is the only correct way
useEffect(() => {
  fetchUser(id).then(user => reset({ name: user.name, email: user.email }));
}, [id, reset]);
```

---

## `reset()` / `setValue` / `trigger`

```tsx
reset();                           // back to defaultValues
reset(newValues);                  // new baseline
reset(values, { keepErrors: false, keepDirty: false });

setValue('country', 'AU', { shouldValidate: true, shouldDirty: true });

// Multi-step form — validate current step before advancing
const ok = await trigger(['email', 'name']);
if (ok) goToNextStep();

// After successful submit
handleSubmit(async (data) => {
  await api.submit(data);
  reset(data);                     // mark form as clean with submitted values as baseline
})(event);
```

---

## Server errors after submit

```tsx
handleSubmit(async (data) => {
  try {
    await api.submit(data);
    reset(data);
  } catch (err) {
    setError('email', { type: 'server', message: 'Email already in use' });
    setError('root', { message: 'Submission failed — try again' });
  }
});

// Render root error
{formState.errors.root && <Text style={s.error}>{formState.errors.root.message}</Text>}
```

---

## `useFieldArray` — Dynamic Lists

```tsx
const AddressSchema = z.object({
  addresses: z.array(z.object({
    street: z.string().min(1, 'Required'),
    city:   z.string().min(1, 'Required'),
  })).min(1, 'Add at least one address'),
});
type AddressForm = z.infer<typeof AddressSchema>;

const { fields, append, remove, move } = useFieldArray({ control, name: 'addresses' });

{fields.map((field, index) => (
  // ✅ always field.id — never index
  <View key={field.id}>
    <FormField control={control} name={`addresses.${index}.street`} placeholder="Street" />
    <FormField control={control} name={`addresses.${index}.city`} placeholder="City" />
    {/* nested error */}
    {formState.errors.addresses?.[index]?.street && (
      <Text>{formState.errors.addresses[index].street.message}</Text>
    )}
    <Pressable onPress={() => remove(index)}><Text>Remove</Text></Pressable>
  </View>
))}
<Pressable onPress={() => append({ street: '', city: '' })}><Text>Add</Text></Pressable>
```

---

## Zod v4 Schema Patterns

### `z.infer` — single source of truth

```tsx
const Schema = z.object({ name: z.string(), age: z.number() });
type Form = z.infer<typeof Schema>; // never write a separate interface
```

### Format validators (v4 top-level)

```tsx
const Schema = z.object({
  email:    z.email('Enter a valid email'),
  website:  z.url('Enter a valid URL').optional(),
  id:       z.uuid(),
  ipAddr:   z.ipv4(),           // or z.ipv6()
  image:    z.base64().optional(),
});
```

### Unified error param (v4)

```tsx
// v3 — dropped in v4
z.string({ invalid_type_error: 'Must be text', required_error: 'Required' })

// v4 — unified error param
z.string({ error: 'Must be text' })

// v4 — error as function for dynamic messages
z.string({
  error: (issue) => issue.code === 'invalid_type' ? 'Must be text' : 'Invalid value'
})
```

### `z.record` — two arguments required in v4

```tsx
// ❌ v3 single-arg — no longer compiles in v4
z.record(z.string())

// ✅ v4 — both key and value schema required
z.record(z.string(), z.string())
z.record(z.string(), z.number())
```

### `z.enum` replaces `z.nativeEnum`

```tsx
// ❌ v3
const Status = z.nativeEnum(StatusEnum);
Status.Enum.active   // .Enum removed in v4
Status.Values        // .Values removed in v4

// ✅ v4 — z.enum accepts TS enums directly
const Status = z.enum(StatusEnum);
Status.enum.active   // .enum is the only accessor
```

### `discriminatedUnion` — O(1) lookup

```tsx
// z.union — O(n) sequential validation
// z.discriminatedUnion — O(1) Map lookup on discriminator field
const PaymentSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('card'), cardNumber: z.string().min(16).max(16) }),
  z.object({ type: z.literal('bank'), accountNumber: z.string().min(8) }),
  z.object({ type: z.literal('crypto'), wallet: z.string() }),
]);
```

### `superRefine` — cross-field, multiple errors

```tsx
const PasswordSchema = z.object({
  password:        z.string().min(8),
  confirmPassword: z.string(),
}).superRefine((data, ctx) => {
  if (data.password !== data.confirmPassword) {
    // Zod v4: code defaults to 'custom' — no need to pass it explicitly
    ctx.addIssue({ message: 'Passwords do not match', path: ['confirmPassword'] });
  }
});
```

### Async `refine` — server-side validation

```tsx
const UsernameSchema = z.object({
  username: z.string().min(3).refine(
    async (val) => !(await api.users.exists(val)),
    { message: 'Username already taken' }
  ),
});
```

### `z.coerce` — TextInput always returns strings

```tsx
const Schema = z.object({
  age:   z.coerce.number({ error: 'Must be a number' }).int().min(18),
  price: z.coerce.number().positive(),
});
```

### transform — validate first, never throw inside

```tsx
// ❌ throw inside transform crashes safeParse — bypasses ZodError entirely
z.string().transform((val) => { if (!val) throw new Error('empty'); return val; });

// ✅ validate with refine/min, transform after
z.string().min(1, 'Required').transform((val) => val.trim().toLowerCase());
```

### `zodResolver` `raw` option — validate without transforming

```tsx
// raw: true — validates but returns original form values (skips transforms)
useForm({ resolver: zodResolver(Schema, undefined, { raw: true }) });
```

---

## Anti-Pattern Hard Stops

| ❌ | ✅ |
|---|---|
| `z.string().email()` | `z.email()` |
| `z.string().url()` | `z.url()` |
| `z.string().uuid()` | `z.uuid()` |
| `z.record(z.string())` | `z.record(z.string(), ValueSchema)` |
| `z.nativeEnum(E)` | `z.enum(E)` |
| `{ invalid_type_error }` / `{ required_error }` | `{ error: '...' }` |
| `.Enum` / `.Values` on z.enum | `.enum` |
| Separate TS interface alongside schema | `type T = z.infer<typeof Schema>` |
| `throw` inside `transform()` | `refine()` before transform |
| `refine()` for multi-field errors | `superRefine()` with `ctx.addIssue({ path })` |
| `z.union` for discriminated shapes | `z.discriminatedUnion('type', [...])` |
| `register()` on RN TextInput | `useController` / `Controller` |
| `watch()` at form root | `useWatch({ control, name })` |
| `mode: 'onChange'` | `mode: 'onBlur'` |
| `{ field: undefined }` in `defaultValues` | `{ field: '' }` or `0` or `null` |
| `index` as key in `useFieldArray` | `field.id` |
| Conditional `formState` sub-property access | Destructure unconditionally |
| `[formState.errors]` in useEffect deps | `[formState]` |
| Numeric TextInput without `z.coerce` | `z.coerce.number()` |
