const REPO = 'nicolettas-muggelbude/RechnungsFee'

export interface DownloadStats {
  windows: number
  linux: number
  macos: number
  total: number
}

export async function getDownloadStats(token?: string): Promise<DownloadStats> {
  let windows = 0, linux = 0, macos = 0

  try {
    const headers: Record<string, string> = token ? { Authorization: `token ${token}` } : {}
    const res = await fetch(
      `https://api.github.com/repos/${REPO}/releases?per_page=100`,
      { headers }
    )
    if (!res.ok) return { windows, linux, macos, total: 0 }

    const releases: Array<{ assets: Array<{ name: string; download_count: number }> }> = await res.json()

    for (const release of releases) {
      for (const asset of release.assets ?? []) {
        const n = asset.name
        const c = asset.download_count ?? 0
        if (n.endsWith('_x64-setup.exe'))  windows += c
        else if (n.endsWith('.AppImage'))   linux   += c
        else if (n.endsWith('.dmg'))        macos   += c
      }
    }
  } catch {}

  return { windows, linux, macos, total: windows + linux + macos }
}
