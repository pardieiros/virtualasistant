# Troubleshooting iOS Build Issues

## "Device is busy (Preparing iPhone)" Error

Se vires este erro ao tentar correr a app no iPhone físico:

```
error:Device is busy (Preparing iPhone de Marco)
```

### Soluções (por ordem):

1. **Espera alguns segundos e tenta novamente**
   ```bash
   flutter run
   ```

2. **Desconecta e reconecta o iPhone**
   - Desconecta o cabo USB (ou desliga wireless)
   - Espera 5 segundos
   - Reconecta
   - No iPhone: confia no computador se pedido

3. **Reinicia o dispositivo no Xcode**
   - Abre Xcode
   - Window → Devices and Simulators
   - Seleciona o iPhone
   - Clica "Unpair" (se necessário) e depois reconecta

4. **Limpa o build do Flutter**
   ```bash
   cd mobileflutter/jarvas
   flutter clean
   flutter pub get
   cd ios
   pod deintegrate  # se tiveres CocoaPods
   pod install
   cd ..
   flutter run
   ```

5. **Usa o simulador iOS temporariamente**
   ```bash
   flutter run -d "iPhone 15 Pro"  # ou outro simulador disponível
   ```

6. **Verifica a ligação wireless (se estás a usar wireless debugging)**
   - No iPhone: Settings → Developer → Network
   - Garante que o iPhone e o Mac estão na mesma rede Wi‑Fi
   - Tenta usar cabo USB em vez de wireless

7. **Reinicia o Xcode e o Flutter daemon**
   ```bash
   killall Xcode
   flutter doctor
   flutter run
   ```

8. **Verifica certificados de desenvolvimento**
   - Xcode → Preferences → Accounts
   - Seleciona a tua conta Apple
   - Clica "Download Manual Profiles"
   - No projeto: Runner → Signing & Capabilities → seleciona o Team correto

### Se nada funcionar:

- Usa o simulador iOS para desenvolvimento: `flutter run`
- Para testar no dispositivo físico, tenta abrir o projeto diretamente no Xcode:
  ```bash
  open ios/Runner.xcworkspace
  ```
  E depois corre a app a partir do Xcode (⌘R).
