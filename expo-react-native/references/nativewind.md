# NativeWind v4 — Tailwind CSS in React Native

> NativeWind v4 targets Tailwind CSS v3 (pinned to `^3.4.17`). v5 (pre-release) targets Tailwind CSS v4.
> Current stable: v4.1.x. Install via `npm install nativewind`.

## Setup (Expo)

```bash
npm install nativewind react-native-reanimated react-native-safe-area-context
npm install --save-dev tailwindcss@^3.4.17 prettier-plugin-tailwindcss
```

**`tailwind.config.js`** — preset is required:
```js
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: { extend: {} },
  plugins: [],
};
```

**`global.css`**:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**`babel.config.js`** — `jsxImportSource` is the v4 replacement for the old `styled()` wrapper:
```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
  };
};
```

**`metro.config.js`**:
```js
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const config = getDefaultConfig(__dirname);
module.exports = withNativeWind(config, { input: './global.css' });
```

**Root layout** — import CSS once at the app entry:
```tsx
// app/_layout.tsx
import '../global.css';
```

**TypeScript** — create `nativewind-env.d.ts` (NOT `nativewind.d.ts` — that name conflicts):
```ts
/// <reference types="nativewind/types" />
```

**`app.json`** — required for web + dark mode:
```json
{
  "expo": {
    "web": { "bundler": "metro" },
    "userInterfaceStyle": "automatic"
  }
}
```

---

## Critical Gotchas

### 1. Always declare both light AND dark variants

React Native requires explicit styles for all states — no cascade, no defaults.

```tsx
// ❌ only dark variant — light is unstyled
<Text className="dark:text-white" />

// ✅ both variants
<Text className="text-black dark:text-white" />
```

### 2. Colors do NOT cascade from View to Text

React Native has no style inheritance. Setting `text-red-500` on a `<View>` does nothing to its children.

```tsx
// ❌ color doesn't reach <Text>
<View className="text-red-500"><Text>This is not red</Text></View>

// ✅ apply directly to Text
<View><Text className="text-red-500">This is red</Text></View>
```

### 3. `hover:` / `focus:` / `active:` only work on compatible components

These pseudo-classes require the component to support the corresponding event props:

| Modifier | Requires | Works on |
|---|---|---|
| `hover:` | `onHoverIn` / `onHoverOut` | `Pressable`, `TextInput` |
| `active:` | `onPressIn` / `onPressOut` | `Pressable` |
| `focus:` | `onFocus` / `onBlur` | `TextInput` |

They do NOT work on plain `<View>` or `<Text>`.

### 4. Flexbox defaults differ from web

| Property | Web default | React Native default |
|---|---|---|
| `flex-direction` | `row` | `column` |
| `align-content` | `stretch` | `flex-start` |
| `flex-shrink` | `1` | `0` |

Always set flex direction explicitly. Use `flex-1` for consistent flex fill behavior.

### 5. Responsive breakpoints are web-sized

NativeWind's default breakpoints (`sm: 640px`, `md: 768px`, etc.) are designed for web screens, not mobile viewports. Override in your theme config for native:

```js
// tailwind.config.js
theme: {
  screens: {
    sm: '380px',
    md: '414px',
    lg: '768px',
  },
}
```

### 6. `userInterfaceStyle: "automatic"` is required for dark mode in Expo

Without this in `app.json`, the device's dark mode setting is ignored.

### 7. Import `useColorScheme` from `"nativewind"` — not `"react-native"`

```tsx
// ❌ react-native — no setColorScheme / toggleColorScheme
import { useColorScheme } from 'react-native';

// ✅ nativewind — adds setColorScheme, toggleColorScheme
import { useColorScheme } from 'nativewind';
const { colorScheme, setColorScheme, toggleColorScheme } = useColorScheme();
```

### 8. No `styled()` wrapper in v4

v4 uses a JSX transform (`jsxImportSource: "nativewind"`). Core RN components accept `className` automatically. Do not use `styled()` — it's a v2 pattern.

---

## Dark Mode

```tsx
// Toggle dark mode
import { useColorScheme } from 'nativewind';

function ThemeToggle() {
  const { colorScheme, toggleColorScheme } = useColorScheme();
  return (
    <Pressable onPress={toggleColorScheme}>
      <Text>{colorScheme === 'dark' ? '☀️' : '🌙'}</Text>
    </Pressable>
  );
}

// Persist selection — setColorScheme accepts 'light' | 'dark' | 'system'
setColorScheme('dark');
```

---

## Dynamic Themes with CSS Variables

```tsx
import { vars } from 'nativewind';

// Define theme tokens
const lightTheme = vars({ '--color-primary': '59 130 246' }); // rgb values, no rgb()
const darkTheme  = vars({ '--color-primary': '147 197 253' });

// Apply at tree root
function Theme({ children }: { children: React.ReactNode }) {
  const { colorScheme } = useColorScheme();
  return (
    <View style={colorScheme === 'dark' ? darkTheme : lightTheme}>
      {children}
    </View>
  );
}

// tailwind.config.js — reference the variable
theme: {
  colors: {
    primary: 'rgb(var(--color-primary) / <alpha-value>)',
  },
}

// Usage
<Text className="text-primary">Themed text</Text>

// Read a CSS variable in JS (unstable API — may change)
import { useUnstableNativeVariable } from 'nativewind';
const primaryColor = useUnstableNativeVariable('--color-primary');
```

---

## Platform-Specific Colors (tailwind.config.js)

```js
const { platformSelect, platformColor } = require('nativewind/theme');

module.exports = {
  theme: {
    extend: {
      colors: {
        // Maps to iOS systemRed, Android colorError, fallback red
        danger: platformSelect({
          ios: platformColor('systemRed'),
          android: platformColor('?android:colorError'),
          default: '#ef4444',
        }),
        // Native separator line color (system-aware)
        separator: platformSelect({
          ios: platformColor('separator'),
          android: platformColor('?android:dividerHorizontal'),
          default: '#e5e7eb',
        }),
      },
    },
  },
};
```

Other theme helpers: `hairlineWidth()`, `pixelRatio()`, `fontScale()`, `getPixelSizeForLayoutSize()`.

---

## Safe Area Insets (CSS)

```css
/* global.css — use env() for safe area */
.header { padding-top: env(safe-area-inset-top); }
.footer { padding-bottom: env(safe-area-inset-bottom); }
```

Or via arbitrary values in className:
```tsx
<View className="pt-[env(safe-area-inset-top)]" />
```

---

## Group / Parent State

```tsx
// Parent state modifies children's styles
<Pressable className="group">
  <Text className="text-gray-600 group-active:text-white">
    Responds to parent press
  </Text>
  <View className="bg-gray-100 group-active:bg-blue-500" />
</Pressable>

// Named groups for nested state
<Pressable className="group/card">
  <Text className="group-hover/card:underline">Card title</Text>
</Pressable>
```

---

## Third-Party Components

Use `remapProps` for components with style props, `cssInterop` for lower-level control. Never use these for your own components.

```tsx
import { remapProps, cssInterop } from 'nativewind';

// Simple style prop remapping
remapProps(ThirdParty, {
  contentContainerClassName: 'contentContainerStyle',
});

// Full interop with native value extraction (e.g. TextInput placeholder color)
cssInterop(TextInput, {
  className: { target: 'style', nativeStyleToProp: { textAlign: true } },
  placeholderClassName: { target: 'placeholderTextColor' },
});
```

---

## Custom Components

```tsx
import { clsx } from 'clsx';

const variants = {
  primary: 'bg-blue-500 text-white',
  secondary: 'bg-gray-100 text-gray-900',
} as const;

function Button({ variant = 'primary', className, ...props }) {
  return (
    <Pressable
      className={clsx('rounded-xl px-4 py-3 active:opacity-80', variants[variant], className)}
      {...props}
    />
  );
}
```

Recommended class merging: `clsx`, `tailwind-variants`, `cva`, `tw-classed`.

---

## Debugging

```bash
# Always clear cache first when styles don't apply
npx expo start --clear

# Verify Tailwind generates output independently
npx tailwindcss --input global.css --output /tmp/out.css

# Enable debug logging
DEBUG=nativewind npx expo start
```

```tsx
// verifyInstallation() — inside a component, not module level
import { verifyInstallation } from 'nativewind';
function App() {
  verifyInstallation(); // logs warnings if setup is incorrect
  return <RootNavigator />;
}
```

**Common issues:**

| Issue | Fix |
|---|---|
| Styles not applied | Clear cache: `npx expo start --clear` |
| Dark mode not working | Add `userInterfaceStyle: "automatic"` to `app.json` |
| Text not colored | Apply color class directly to `<Text>`, not parent `<View>` |
| `hover:` has no effect | Component must support `onHoverIn`/`onHoverOut` (use `Pressable`) |
| Conditional class not applying | Declare both variants: `text-black dark:text-white` |
| TypeScript errors | File must be named `nativewind-env.d.ts`, not `nativewind.d.ts` |
| `inlineAnimations` breaks HMR | Remove `experiments.inlineAnimations` from metro config |
