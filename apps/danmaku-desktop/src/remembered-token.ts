import { readFile, writeFile } from "node:fs/promises";

const MAX_REMEMBERED_TOKEN_LENGTH = 4096;

export type SecureTokenStorage = {
  isEncryptionAvailable: () => boolean;
  encryptString: (plainText: string) => Buffer;
  decryptString: (encrypted: Buffer) => string;
};

export type TokenFileSystem = {
  readFile: (filePath: string) => Promise<Buffer>;
  writeFile: (filePath: string, data: Buffer, options: { mode: number }) => Promise<void>;
};

const defaultFileSystem: TokenFileSystem = {
  readFile: (filePath) => readFile(filePath),
  writeFile: (filePath, data, options) => writeFile(filePath, data, options),
};

const normalizeToken = (value: string): string => {
  const token = value.trim();
  return token.length > 0 && token.length <= MAX_REMEMBERED_TOKEN_LENGTH ? token : "";
};

export async function loadRememberedToken(
  filePath: string,
  secureStorage: SecureTokenStorage,
  fileSystem: TokenFileSystem = defaultFileSystem,
): Promise<string> {
  try {
    if (!secureStorage.isEncryptionAvailable()) return "";
    return normalizeToken(secureStorage.decryptString(await fileSystem.readFile(filePath)));
  } catch {
    return "";
  }
}

export async function saveRememberedToken(
  filePath: string,
  token: string,
  secureStorage: SecureTokenStorage,
  fileSystem: TokenFileSystem = defaultFileSystem,
): Promise<boolean> {
  const normalizedToken = normalizeToken(token);
  if (!normalizedToken) return false;
  try {
    if (!secureStorage.isEncryptionAvailable()) return false;
    const encrypted = secureStorage.encryptString(normalizedToken);
    await fileSystem.writeFile(filePath, encrypted, { mode: 0o600 });
    return true;
  } catch {
    return false;
  }
}
