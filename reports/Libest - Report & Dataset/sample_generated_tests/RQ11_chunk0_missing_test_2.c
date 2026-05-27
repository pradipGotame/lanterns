/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ11_chunk0_missing_test_2.c
 */

#include <CUnit/CUnit.h>
#include <openssl/x509.h>
#include <openssl/pem.h>
#include <openssl/evp.h>
#include <openssl/bio.h>
#include "est.h"

/*
 * Forward declarations for helpers shown in exemplars
 */
EVP_PKEY *generate_ec_private_key(int nid);
int populate_x509_request(X509_REQ *req, EVP_PKEY *pkey, const char *cn);

static void rq11_chunk0_missing_test_2(void)
{
    X509_REQ *req = NULL;
    X509_REQ *req_parsed = NULL;
    X509_REQ *req_no_pop = NULL;
    X509_REQ *req_no_parsed = NULL;
    EVP_PKEY *key = NULL;
    EVP_PKEY *pub = NULL;
    BIO *mem = NULL;
    int rv;
    int idx;
    int verify_ret;

    LOG_FUNC_NM
    ;

    /* generate a private key */
    key = generate_ec_private_key(NID_secp384r1);
    CU_ASSERT(key != NULL);

    /* build a CSR that includes PoP (challengePassword) */
    req = X509_REQ_new();
    CU_ASSERT(req != NULL);

    rv = populate_x509_request(req, key, "Test CSR");
    CU_ASSERT(rv == EST_ERR_NONE);

    /* sign the request so signature verification can be performed */
    rv = X509_REQ_sign(req, key, EVP_sha256());
    CU_ASSERT(rv == 1);

    /* serialize to DER (simulate client->server transport) */
    mem = BIO_new(BIO_s_mem());
    CU_ASSERT(mem != NULL);
    rv = i2d_X509_REQ_bio(mem, req);
    CU_ASSERT(rv == 1);

    /* server-side parsing via d2i_X509_REQ_bio */
    req_parsed = d2i_X509_REQ_bio(mem, NULL);
    CU_ASSERT(req_parsed != NULL);

    /* verify the CSR signature (server should verify signature) */
    pub = X509_REQ_get_pubkey(req_parsed);
    CU_ASSERT(pub != NULL);
    verify_ret = X509_REQ_verify(req_parsed, pub);
    CU_ASSERT(verify_ret == 1);
    EVP_PKEY_free(pub);

    /* assert challengePassword (PoP) attribute is present (positive PoP case) */
    idx = X509_REQ_get_attr_by_NID(req_parsed, NID_pkcs9_challengePassword, -1);
    CU_ASSERT(idx >= 0);

    /* Negative case: construct a CSR without challengePassword and ensure attribute is absent */
    BIO_free(mem);
    mem = BIO_new(BIO_s_mem());
    CU_ASSERT(mem != NULL);

    req_no_pop = X509_REQ_new();
    CU_ASSERT(req_no_pop != NULL);

    /* set public key but do NOT add challengePassword */
    rv = X509_REQ_set_pubkey(req_no_pop, key);
    CU_ASSERT(rv == 1);

    rv = X509_REQ_sign(req_no_pop, key, EVP_sha256());
    CU_ASSERT(rv == 1);

    rv = i2d_X509_REQ_bio(mem, req_no_pop);
    CU_ASSERT(rv == 1);

    req_no_parsed = d2i_X509_REQ_bio(mem, NULL);
    CU_ASSERT(req_no_parsed != NULL);

    idx = X509_REQ_get_attr_by_NID(req_no_parsed, NID_pkcs9_challengePassword, -1);
    /* attribute missing -> server PoP check would reject (EST_ERR_AUTH_FAIL_TLSUID) */
    CU_ASSERT(idx == -1);

    /* cleanup */
    X509_REQ_free(req);
    X509_REQ_free(req_parsed);
    X509_REQ_free(req_no_pop);
    X509_REQ_free(req_no_parsed);
    BIO_free(mem);
    EVP_PKEY_free(key);
}
