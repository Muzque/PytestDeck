const indexCache = new WeakMap()

export const isSameTestNodeId = (idA, idB) => {
  if (!idA || !idB) return false
  const normA = idA.replace(/\\/g, '/')
  const normB = idB.replace(/\\/g, '/')
  if (normA === normB) return true
  const sepA = normA.indexOf('::')
  const sepB = normB.indexOf('::')
  if (sepA === -1 || sepB === -1) {
    return normA.endsWith('/' + normB) || normB.endsWith('/' + normA)
  }
  const tailA = normA.slice(sepA)
  const tailB = normB.slice(sepB)
  if (tailA !== tailB) return false
  const fileA = normA.slice(0, sepA)
  const fileB = normB.slice(0, sepB)
  return fileA === fileB || fileA.endsWith('/' + fileB) || fileB.endsWith('/' + fileA)
}

const extractLookupTail = (id) => {
  const norm = id.replace(/\\/g, '/')
  const sep = norm.indexOf('::')
  if (sep !== -1) {
    return norm.slice(sep)
  }
  const slash = norm.lastIndexOf('/')
  return slash !== -1 ? norm.slice(slash + 1) : norm
}

const getOutputsIndex = (outputs) => {
  let entry = indexCache.get(outputs)
  if (entry) return entry
  const byTail = new Map()
  for (const key of Object.keys(outputs)) {
    if (!outputs[key]) continue
    const tail = extractLookupTail(key)
    let bucket = byTail.get(tail)
    if (!bucket) {
      bucket = []
      byTail.set(tail, bucket)
    }
    bucket.push(key)
  }
  entry = {
    byTail,
    resolvedKeys: new Map()
  }
  indexCache.set(outputs, entry)
  return entry
}

export const findNodeKey = (outputs, id) => {
  if (!id || !outputs || typeof outputs !== 'object') return null
  if (outputs[id]) return id
  const index = getOutputsIndex(outputs)
  if (index.resolvedKeys.has(id)) {
    return index.resolvedKeys.get(id)
  }
  const tail = extractLookupTail(id)
  const candidates = index.byTail.get(tail)
  if (!candidates || candidates.length === 0) {
    index.resolvedKeys.set(id, null)
    return null
  }
  let bestKey = null
  let bestDiff = Infinity
  for (const key of candidates) {
    if (outputs[key] && isSameTestNodeId(id, key)) {
      const diff = Math.abs(id.length - key.length)
      if (diff < bestDiff) {
        bestDiff = diff
        bestKey = key
      }
    }
  }
  index.resolvedKeys.set(id, bestKey)
  return bestKey
}

export const findNodeRecord = (outputs, id) => {
  if (!id || !outputs || typeof outputs !== 'object') return null
  if (outputs[id]) return outputs[id]
  const key = findNodeKey(outputs, id)
  return key ? outputs[key] : null
}
