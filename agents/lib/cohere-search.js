/**
 * Vaal AI Empire - Cohere Semantic Search Library
 * 
 * This library enables AI agents to perform semantic search over knowledge bases
 * using Cohere's embed-english-v3.0 model and rerank-english-v2.0.
 * 
 * Based on: https://docs.cohere.com/page/cookbooks/embed-jobs
 */

const cohere = require('cohere-ai');
const hnswlib = require('hnswlib-node');
const fs = require('fs');
const path = require('path');

class CohereSemanticSearch {
  constructor(apiKey) {
    this.client = cohere.Client(apiKey || process.env.COHERE_API_KEY);
    this.indexes = new Map(); // Store multiple indexes for different knowledge bases
    this.embeddings = new Map(); // Cache embeddings
    this.texts = new Map(); // Cache original texts
  }

  /**
   * Initialize a knowledge base index from JSON data
   * @param {string} name - Index name (e.g., 'sars_regulations', 'crisis_data')
   * @param {Array} documents - Array of document objects with 'text' field
   * @param {Object} options - Configuration options
   */
  async initializeIndex(name, documents, options = {}) {
    const {
      model = 'embed-english-v3.0',
      inputType = 'search_document',
      dim = 1024,
      space = 'ip', // inner product
      maxElements = 10000,
      efConstruction = 512,
      M = 64
    } = options;

    console.log(`[CohereSearch] Initializing index: ${name}`);
    console.log(`[CohereSearch] Documents to embed: ${documents.length}`);

    // Extract texts from documents
    const texts = documents.map(doc => {
      if (typeof doc === 'string') return doc;
      if (doc.text) return doc.text;
      if (doc.content) return doc.content;
      return JSON.stringify(doc);
    });

    // Generate embeddings using Cohere
    console.log(`[CohereSearch] Generating embeddings with ${model}...`);
    const embedResponse = await this.client.embed({
      texts: texts,
      model: model,
      inputType: inputType,
      truncate: 'END'
    });

    const embeddings = embedResponse.embeddings;
    console.log(`[CohereSearch] Generated ${embeddings.length} embeddings`);

    // Initialize HNSW index
    const index = new hnswlib.HierarchicalNSW(space, dim);
    index.initIndex(maxElements, efConstruction, M);

    // Add embeddings to index
    embeddings.forEach((embedding, idx) => {
      index.addPoint(embedding, idx);
    });

    console.log(`[CohereSearch] Index ${name} initialized with ${embeddings.length} vectors`);

    // Store index and data
    this.indexes.set(name, index);
    this.embeddings.set(name, embeddings);
    this.texts.set(name, texts);

    return {
      name,
      documents: embeddings.length,
      model,
      dim
    };
  }

  /**
   * Search a knowledge base index
   * @param {string} indexName - Name of the index to search
   * @param {string} query - Search query
   * @param {Object} options - Search options
   */
  async search(indexName, query, options = {}) {
    const {
      k = 10, // Number of results to retrieve
      rerank = true, // Whether to use Cohere rerank
      topN = 3, // Number of results after reranking
      rerankModel = 'rerank-english-v2.0',
      includeScores = true
    } = options;

    // Check if index exists
    if (!this.indexes.has(indexName)) {
      throw new Error(`Index ${indexName} not found. Initialize it first.`);
    }

    const index = this.indexes.get(indexName);
    const texts = this.texts.get(indexName);

    console.log(`[CohereSearch] Searching index: ${indexName}`);
    console.log(`[CohereSearch] Query: ${query}`);

    // Generate query embedding
    const queryEmbedResponse = await this.client.embed({
      texts: [query],
      model: 'embed-english-v3.0',
      inputType: 'search_query',
      truncate: 'END'
    });

    const queryEmbedding = queryEmbedResponse.embeddings[0];

    // Search index
    const result = index.searchKnn(queryEmbedding, k);
    const docIndices = result.neighbors;

    // Retrieve documents
    const retrievedDocs = docIndices.map(idx => ({
      text: texts[idx],
      index: idx
    }));

    console.log(`[CohereSearch] Retrieved ${retrievedDocs.length} candidates`);

    // Rerank if enabled
    if (rerank && retrievedDocs.length > 0) {
      console.log(`[CohereSearch] Reranking with ${rerankModel}...`);
      
      const rerankResponse = await this.client.rerank({
        query: query,
        documents: retrievedDocs.map(d => d.text),
        model: rerankModel,
        topN: Math.min(topN, retrievedDocs.length)
      });

      const rankedResults = rerankResponse.results.map((r, rank) => ({
        rank: rank + 1,
        text: r.document.text,
        originalIndex: retrievedDocs[r.index].index,
        relevanceScore: r.relevanceScore,
        ...(includeScores && { score: r.relevanceScore })
      }));

      console.log(`[CohereSearch] Reranked to top ${rankedResults.length} results`);
      return rankedResults;
    }

    // Return without reranking
    return retrievedDocs.slice(0, topN).map((doc, rank) => ({
      rank: rank + 1,
      text: doc.text,
      originalIndex: doc.index,
      ...(includeScores && { score: result.distances[rank] })
    }));
  }

  /**
   * Save index to disk for persistence
   * @param {string} indexName - Name of index to save
   * @param {string} filepath - Path to save index
   */
  saveIndex(indexName, filepath) {
    if (!this.indexes.has(indexName)) {
      throw new Error(`Index ${indexName} not found`);
    }

    const index = this.indexes.get(indexName);
    const texts = this.texts.get(indexName);

    // Save HNSW index
    index.writeIndexSync(filepath + '.hnsw');

    // Save texts as JSON
    fs.writeFileSync(
      filepath + '.texts.json',
      JSON.stringify(texts, null, 2)
    );

    console.log(`[CohereSearch] Index ${indexName} saved to ${filepath}`);
  }

  /**
   * Load index from disk
   * @param {string} indexName - Name to assign to loaded index
   * @param {string} filepath - Path to load index from
   * @param {Object} options - Configuration options
   */
  loadIndex(indexName, filepath, options = {}) {
    const {
      dim = 1024,
      space = 'ip',
      maxElements = 10000
    } = options;

    // Load HNSW index
    const index = new hnswlib.HierarchicalNSW(space, dim);
    index.readIndexSync(filepath + '.hnsw', maxElements);

    // Load texts
    const texts = JSON.parse(
      fs.readFileSync(filepath + '.texts.json', 'utf-8')
    );

    // Store
    this.indexes.set(indexName, index);
    this.texts.set(indexName, texts);

    console.log(`[CohereSearch] Index ${indexName} loaded from ${filepath}`);
    console.log(`[CohereSearch] Documents: ${texts.length}`);

    return {
      name: indexName,
      documents: texts.length,
      dim
    };
  }
}

module.exports = CohereSemanticSearch;
