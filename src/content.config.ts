import { defineCollection } from 'astro:content'
import { glob } from 'astro/loaders'

export const collections = {
  handbuch: defineCollection({
    loader: glob({ pattern: '**/*.md', base: './src/content/handbuch' }),
  }),
}
