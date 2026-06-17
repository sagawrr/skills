# NativeWind — className Patterns

> v4 (stable): Tailwind CSS v3. v5 (beta): Tailwind CSS v4 — not yet production-stable.

---

## v4 → v5 Migration (code-level changes only)

v5 removes the JSX transform. Two source-code changes required (both verified):

1. Remove `jsxImportSource: 'nativewind'` from Babel config
2. Remove `'nativewind/babel'` from Babel presets

v5 does **not** require New Architecture (verified refuted). `vars()` still works in v5 (not replaced).

---

## Critical Gotchas

### Always declare both light AND dark variants

```tsx
// ❌ light variant unstyled — invisible on light mode
<Text className="dark:text-white" />

// ✅
<Text className="text-black dark:text-white" />
```

### Text color does NOT cascade from View to Text

```tsx
// ❌ setting color on View does nothing to child Text
<View className="text-red-500"><Text>not red</Text></View>

// ✅ apply directly to Text
<View><Text className="text-red-500">red</Text></View>
```

### `hover:` / `focus:` / `active:` only work on compatible components

| Modifier | Requires event props | Works on |
|---|---|---|
| `hover:` | `onHoverIn` / `onHoverOut` | `Pressable`, `TextInput` |
| `active:` | `onPressIn` / `onPressOut` | `Pressable` |
| `focus:` | `onFocus` / `onBlur` | `TextInput` |

Does NOT work on plain `<View>` or `<Text>`.

### Flexbox defaults differ from web

| Property | Web | React Native |
|---|---|---|
| `flex-direction` | `row` | `column` |
| `flex-shrink` | `1` | `0` |

Always set flex direction explicitly. Use `flex-1` to fill available space.

---

## Dark Mode

```tsx
import { useColorScheme } from 'nativewind'; // NOT from 'react-native'

function ThemeToggle() {
  const { colorScheme, toggleColorScheme } = useColorScheme();
  return <Pressable onPress={toggleColorScheme}><Text>{colorScheme}</Text></Pressable>;
}

// setColorScheme accepts 'light' | 'dark' | 'system'
setColorScheme('dark');
```

---

## CSS Variables (Dynamic Themes)

```tsx
import { vars } from 'nativewind';

const lightTheme = vars({ '--color-primary': '59 130 246' }); // space-separated RGB, no rgb()
const darkTheme  = vars({ '--color-primary': '147 197 253' });

function Theme({ children }: { children: React.ReactNode }) {
  const { colorScheme } = useColorScheme();
  return <View style={colorScheme === 'dark' ? darkTheme : lightTheme}>{children}</View>;
}

// Use in className — reference the variable
<Text className="text-[rgb(var(--color-primary))]">Themed</Text>
```

---

## Group / Parent State

```tsx
// Parent state affects children
<Pressable className="group">
  <Text className="text-gray-600 group-active:text-white">Responds to parent press</Text>
  <View className="bg-gray-100 group-active:bg-blue-500" />
</Pressable>

// Named groups for nested control
<Pressable className="group/card">
  <Text className="group-hover/card:underline">Card title</Text>
</Pressable>
```

---

## Custom Components

```tsx
import { clsx } from 'clsx';

const variants = {
  primary: 'bg-blue-500 text-white active:bg-blue-600',
  ghost:   'bg-transparent text-blue-500 active:bg-blue-50',
} as const;

function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  return (
    <Pressable
      className={clsx('rounded-xl px-4 py-3', variants[variant], className)}
      {...props}
    />
  );
}
```

Inline `style` takes precedence over `className` — use for dynamic values not expressible as classes.

---

## Third-Party Components

Use `remapProps` for simple style prop remapping, `cssInterop` for full interop. Never for your own components.

```tsx
import { remapProps, cssInterop } from 'nativewind';

// Map a className prop to an existing style prop
remapProps(ThirdPartyList, { contentContainerClassName: 'contentContainerStyle' });

// Full interop with native value extraction
cssInterop(TextInput, {
  className: { target: 'style', nativeStyleToProp: { textAlign: true } },
  placeholderClassName: { target: 'placeholderTextColor' },
});
```

---

## Debugging

```tsx
// verifyInstallation must be inside a component body — not module level
import { verifyInstallation } from 'nativewind';
function App() {
  verifyInstallation();
  return <RootNavigator />;
}
```

Common issues not covered above:

| Issue | Fix |
|---|---|
| Dark mode not responding | `userInterfaceStyle: "automatic"` must be set in app.json |
| `useColorScheme` missing `setColorScheme` | Import from `'nativewind'`, not `'react-native'` |
