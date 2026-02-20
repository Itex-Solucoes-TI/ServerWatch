# Chaves de licença

**Vendor (quem distribui o ServerWatch):**
1. Na raiz do projeto: `python3 scripts/generate_license_keys.py`
2. Copie `license_public.pem` para esta pasta (já criada pelo script)
3. Inclua `license_public.pem` no build da imagem Docker
4. Guarde `license_private.pem` em local seguro — nunca no servidor do cliente
5. Para gerar tokens: `python3 scripts/generate_license_token.py <cnpj14digitos> <YYYY-MM-DD>`

**Cliente:** recebe apenas o token de licença para ativar no login.
