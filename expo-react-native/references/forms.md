# Forms — React Hook Form v7 + Zod v3

> Verified: react-hook-form.com/docs, zod.dev, @hookform/resolvers source, RHF v7.79.0 bundle

---

## Setup

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// 1. Define schema
const LoginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

// 2. Infer type from schema — never write a separate interface
type LoginForm = z.infer<typeof LoginSchema>;

// 3. Wire up
const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
  resolver: zodResolver(LoginSchema),
  defaultValues: { email: '', password: '' }, // always provide — never undefined
  mode: 'onBlur',      // NOT onChange — see performance section
  reValidateMode: 'onChange', // re-validate on change after first submit
});
```

---

## React Native: always `useController` — never `register()`

`register()` spreads refs onto DOM elements. React Native TextInput doesn't support ref-spreading the same way. **Always use `useController` or `Controller` in RN.**

```tsx
import { useController, Control } from 'react-hook-form';

// Reusable controlled input component
function FormInput({
  control,
  name,
  placeholder,
  secureTextEntry,
}: {
  control: Control<LoginForm>;
  name: keyof LoginForm;
  placeholder?: string;
  secureTextEntry?: boolean;
}) {
  const { field, fieldState: { error } } = useController({ control, name });

  return (
    <>
      <TextInput
        value={field.value}
        onChangeText={field.onChange}  // NOT onChangeText={e => field.onChange(e)}
        onBlur={field.onBlur}
        placeholder={placeholder}
        secureTextEntry={secureTextEntry}
      />
      {error && <Text style={styles.error}>{error.message}</Text>}
    </>
  );
}

// Usage
<FormInput control={control} name="email" placeholder="Email" />
<FormInput control={control} name="password" secureTextEntry />
```

`fieldState.error` gives the field-level error — prefer this over `formState.errors.fieldName`.

---

## formState Proxy — The Subscription Trap

`formState` is a JavaScript Proxy. **A property subscription only activates when the getter is actually called.** Conditional access silently breaks reactivity — the component will not re-render when that property changes.

```tsx
// ❌ short-circuit skips the isValid getter — subscription never activates
const isDisabled = !formState.isDirty || !formState.isValid;

// ✅ read both unconditionally
const { isDirty, isValid } = formState;
const isDisabled = !isDirty || !isValid;

// ❌ [formState.errors] in useEffect — Proxy getter fires once at declaration,
//    not on subsequent changes — effect never re-runs when errors update
useEffect(() => { console.log(errors); }, [formState.errors]);

// ✅ depend on formState itself
useEffect(() => { console.log(formState.errors); }, [formState]);
```

**Rule: destructure formState at the top of the component, unconditionally.**

---

## `watch` vs `useWatch` vs `getValues`

| API | Re-renders | Use when |
|-----|-----------|----------|
| `watch('field')` | Yes — entire form tree | Rarely needed; prefer `useWatch` |
| `useWatch({ control, name })` | Yes — isolated to calling component | Reactively show/hide UI based on a field value |
| `getValues('field')` | Never | Reading value in callbacks, `onSubmit`, side effects |
| `subscribe` (v8+) | Opt-in | Fine-grained subscription (not yet stable in v7) |

```tsx
// ❌ watch at form root — re-renders the whole form on every keystroke
const country = watch('country');

// ✅ useWatch — re-renders only the component that calls it
const country = useWatch({ control, name: 'country' });

// ✅ getValues — no re-render; use inside callbacks
const onConfirm = () => {
  const values = getValues(); // snapshot of current values
  analytics.track('form_confirmed', values);
};
```

---

## Validation Mode

```tsx
// ❌ onChange — validates every keystroke
// RHF docs explicitly warn: "often comes with a significant impact on performance"
useForm({ mode: 'onChange' });

// ✅ onBlur — validates when user leaves the field (best UX + perf for most forms)
useForm({ mode: 'onBlur' });

// ✅ onSubmit (default) — validates only on submit; re-validates onChange after first submit
useForm({ mode: 'onSubmit', reValidateMode: 'onChange' });
```

---

## `defaultValues` — Caching Rules

```tsx
// ❌ undefined defaultValue — conflicts with controlled component state
useForm({ defaultValues: { name: undefined } });

// ❌ async defaultValues via separate setState — race condition on first render
const [defaults, setDefaults] = useState({});
useEffect(() => { fetchUser().then(setDefaults); }, []);
useForm({ defaultValues: defaults }); // defaults is {} on first render, values ignored after

// ✅ async defaultValues — RHF suspends and waits for the promise
useForm({ defaultValues: async () => fetchUser() });

// ✅ updating defaults after init — reset() is the only correct way
const { reset } = useForm({ defaultValues: { name: '' } });
useEffect(() => {
  fetchUser(id).then(user => reset({ name: user.name }));
}, [id, reset]);

// ❌ re-passing new defaultValues to useForm — has NO effect after mount
useForm({ defaultValues: newUser }); // cached values remain unchanged
```

---

## `reset()` patterns

```tsx
// Reset to original defaultValues
reset();

// Reset to specific values (replaces all fields)
reset({ email: user.email, password: '' });

// Reset without triggering validation
reset(values, { keepErrors: false, keepDirty: false });

// After successful submit — reset dirty state
handleSubmit(async (data) => {
  await submitForm(data);
  reset(data); // mark as clean with submitted values as new baseline
})(event);
```

---

## `setValue` vs `trigger`

```tsx
// setValue — programmatically set a field value
setValue('country', 'AU');

// setValue with side effects
setValue('country', 'AU', {
  shouldValidate: true,  // run validation after setting
  shouldDirty: true,     // mark field as dirty
  shouldTouch: true,     // mark field as touched
});

// trigger — manually run validation without changing values
await trigger('email');           // single field
await trigger(['email', 'phone']); // multiple fields
await trigger();                   // all fields

// Pattern: validate step before advancing in a multi-step form
const canAdvance = await trigger(['email', 'name']);
if (canAdvance) goToNextStep();
```

---

## `useFieldArray` — Dynamic Lists

```tsx
import { useFieldArray } from 'react-hook-form';

const AddressSchema = z.object({
  addresses: z.array(z.object({
    street: z.string().min(1),
    city: z.string().min(1),
  })).min(1, 'Add at least one address'),
});

type AddressForm = z.infer<typeof AddressSchema>;

function AddressForm() {
  const { control, handleSubmit } = useForm<AddressForm>({
    resolver: zodResolver(AddressSchema),
    defaultValues: { addresses: [{ street: '', city: '' }] },
  });

  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'addresses',
  });

  return (
    <>
      {fields.map((field, index) => (
        // ❌ never use index as key for useFieldArray — use field.id
        <View key={field.id}>
          <FormInput control={control} name={`addresses.${index}.street`} />
          <FormInput control={control} name={`addresses.${index}.city`} />
          <Pressable onPress={() => remove(index)}><Text>Remove</Text></Pressable>
        </View>
      ))}
      <Pressable onPress={() => append({ street: '', city: '' })}>
        <Text>Add address</Text>
      </Pressable>
    </>
  );
}
```

**Rules:**
- Always use `field.id` as the React `key`, never `index`
- `append()` / `prepend()` / `insert()` add fields; `remove(index)` removes
- `move(from, to)` for drag-to-reorder
- Access nested errors: `formState.errors.addresses?.[index]?.street?.message`

---

## Zod Schema Patterns

### Always `z.infer` — never write a separate type

```tsx
const Schema = z.object({ name: z.string(), age: z.number() });

// ❌ duplicates the schema — drifts over time
interface FormData { name: string; age: number; }

// ✅ single source of truth
type FormData = z.infer<typeof Schema>;
```

### `discriminatedUnion` over `union` for variant schemas

`z.union` tries each option sequentially (O(n)). `z.discriminatedUnion` does an O(1) Map lookup on the discriminator field.

```tsx
// ❌ z.union — validates all shapes until one matches
const PaymentSchema = z.union([
  z.object({ type: z.literal('card'), cardNumber: z.string() }),
  z.object({ type: z.literal('bank'), accountNumber: z.string() }),
]);

// ✅ z.discriminatedUnion — O(1) lookup on 'type' field
const PaymentSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('card'), cardNumber: z.string().min(16).max(16) }),
  z.object({ type: z.literal('bank'), accountNumber: z.string().min(8) }),
]);
```

### `superRefine` for cross-field and multi-error validation

`refine()` = one error. `superRefine()` = multiple errors, custom paths, any issue type.

```tsx
const PasswordSchema = z.object({
  password: z.string(),
  confirmPassword: z.string(),
}).superRefine((data, ctx) => {
  if (data.password !== data.confirmPassword) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Passwords do not match',
      path: ['confirmPassword'], // error appears on confirmPassword field
    });
  }
  if (data.password.length < 8) {
    ctx.addIssue({
      code: z.ZodIssueCode.too_small,
      minimum: 8,
      type: 'string',
      inclusive: true,
      message: 'Password must be at least 8 characters',
      path: ['password'],
    });
  }
});
```

### Async `refine` for server-side validation

```tsx
const UsernameSchema = z.object({
  username: z.string().min(3).refine(
    async (val) => !(await api.users.exists(val)),
    { message: 'Username already taken' }
  ),
});

// zodResolver handles async refinements — no extra setup needed
useForm({ resolver: zodResolver(UsernameSchema) });
```

### `z.coerce` for TextInput numeric values

TextInput always returns strings. Use `z.coerce` to convert before validation.

```tsx
const AgeSchema = z.object({
  age: z.coerce.number().int().min(18, 'Must be at least 18'),
  price: z.coerce.number().positive('Must be positive'),
});

// TextInput value '25' → coerced to number 25 → validated as number
<FormInput control={control} name="age" keyboardType="numeric" />
```

### `transform` — run only after validation passes; never throw inside

```tsx
// ❌ throwing inside transform crashes safeParse — bypasses ZodError entirely
const BadSchema = z.string().transform((val) => {
  if (!val) throw new Error('empty'); // uncaught — not a ZodError
  return val.trim();
});

// ✅ validate first with refine/superRefine, transform after
const GoodSchema = z.string()
  .min(1, 'Required')
  .transform((val) => val.trim().toLowerCase()); // only runs if min(1) passes
```

### Custom error messages — always at the schema level

```tsx
// ❌ generic messages — unhelpful to the user
z.string().min(1)
z.number().max(100)

// ✅ user-facing messages at point of definition
const Schema = z.object({
  email:    z.string().email('Enter a valid email address'),
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(20, 'Username cannot exceed 20 characters')
    .regex(/^[a-z0-9_]+$/, 'Only lowercase letters, numbers, and underscores'),
  age:      z.coerce.number({ invalid_type_error: 'Age must be a number' })
    .int('Age must be a whole number')
    .min(13, 'Must be at least 13 to register'),
});
```

### `zodResolver` `raw` option — validation without transforms

When you want Zod to validate but not transform the submitted data:

```tsx
// raw: true — returns original form values, skips transforms
useForm({
  resolver: zodResolver(Schema, undefined, { raw: true }),
});
```

---

## Submit Pattern

```tsx
const onSubmit = handleSubmit(async (data) => {
  // data is fully typed as z.infer<typeof Schema>
  // data is already validated and transformed by Zod
  try {
    await api.submit(data);
    reset(data);
  } catch (err) {
    // Set server errors back onto specific fields
    setError('email', { type: 'server', message: 'Email already in use' });
  }
});

// Error state for the whole form (server errors, network failures)
const { isSubmitting, isSubmitSuccessful, errors } = formState;
```

---

## Anti-Pattern Hard Stops

| ❌ Anti-pattern | ✅ Fix |
|---|---|
| `register()` on RN TextInput | `useController` / `Controller` always |
| `watch('field')` at form root | `useWatch({ control, name })` in the consuming component |
| `mode: 'onChange'` | `mode: 'onBlur'` or `mode: 'onSubmit'` |
| `defaultValues: { field: undefined }` | Always a concrete value: `''`, `0`, `null` |
| Updating `defaultValues` by re-calling `useForm` | `reset(newValues)` |
| Separate TypeScript interface alongside schema | `type T = z.infer<typeof Schema>` only |
| `z.union` for discriminated shapes | `z.discriminatedUnion('type', [...])` |
| `throw` inside `transform()` | Use `refine()` or `superRefine()` before transform |
| `refine()` for cross-field errors | `superRefine()` with `ctx.addIssue({ path })` |
| `index` as key in `useFieldArray` | `field.id` from the fields array |
| `formState.errors.field` in conditional | Destructure `{ errors }` from `formState` unconditionally |
| `[formState.errors]` in `useEffect` deps | `[formState]` — Proxy getter must fire unconditionally |
| `getValues()` for reactive UI | `useWatch` for reactive, `getValues` for callbacks only |
| Numeric TextInput without `z.coerce` | `z.coerce.number()` to convert string → number |
| Generic Zod error messages | User-facing messages at schema definition |
