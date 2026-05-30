# Capacitor Bridge Code Examples

## JS plugin interface (src/plugins/)
```typescript
import { registerPlugin } from '@capacitor/core';

export interface CameraPlugin {
  takePhoto(options: { quality: number }): Promise<{ path: string }>;
}

const CameraPlugin = registerPlugin<CameraPlugin>('CameraPlugin', {
  web: () => import('./CameraPluginWeb').then(m => new m.CameraPluginWeb()),
});
export default CameraPlugin;
```

## Web fallback (src/plugins/[Name]Web.ts)
```typescript
import { WebPlugin } from '@capacitor/core';
export class CameraPluginWeb extends WebPlugin implements CameraPlugin {
  async takePhoto(options: { quality: number }): Promise<{ path: string }> {
    throw new Error('Camera requires the Android app. Use file upload instead.');
  }
}
```

## Native plugin (Kotlin)
```kotlin
@CapacitorPlugin(name = "CameraPlugin")
class CameraPlugin : Plugin() {
    @PluginMethod
    fun takePhoto(call: PluginCall) {
        val quality = call.getInt("quality", 90)
        // native implementation
        call.resolve(JSObject().apply { put("path", "/path/to/photo.jpg") })
    }
}
```

## Register in MainActivity
```kotlin
class MainActivity : BridgeActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        registerPlugin(CameraPlugin::class.java)
        super.onCreate(savedInstanceState)
    }
}
```

## Build commands
```bash
npm run build && npx cap sync android   # always run before testing on device
npx cap open android                    # open in Android Studio
npx cap run android                     # run on connected device
npx cap copy android                    # copy web assets only (no native deps changed)
```

## Test mock (Vitest)
```typescript
vi.mock('@/plugins/CameraPlugin', () => ({
  default: { takePhoto: vi.fn().mockResolvedValue({ path: '/mock/photo.jpg' }) },
}));
```