/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ11_chunk0_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* globals used by existing tests/log-search helpers */
extern char *log_search_target;
extern int search_target_found;

static void rq11_chunk0_missing_test_1(void)
{
    X509_REQ *req = NULL;
    EVP_PKEY *key = NULL;
    int rv;
    EST_CTX *ctx = NULL;

    LOG_FUNC_NM
    ;

    /* Restart the server (PoP enabled path by default) */
    st_stop();
    us1005_start_server(0, 0, 0, 0);

    /* Ensure CSR attributes include challengePassword (default) */
    st_set_csrattrs(NULL);
    st_disable_csr_cb();

    /* generate a private key */
    key = generate_ec_private_key(NID_secp384r1);
    CU_ASSERT(key != NULL);

    /* build the CSR */
    req = X509_REQ_new();
    CU_ASSERT(req != NULL);

    rv = populate_x509_request(req, key, "RQ11-01");
    CU_ASSERT(rv == EST_ERR_NONE);

    /* Create a client context and force inclusion of PoP in CSR */
    ctx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ctx != NULL);

    rv = est_client_force_pop(ctx);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * Ensure the server does not log a DER parsing error when we submit
     * a properly constructed CSR (indirectly asserting d2i_X509_REQ_bio succeeded).
     */
    log_search_target = "Problem reading DER encoded certificate request";
    search_target_found = 0;

    /* Submit the CSR to the server using the existing provision helper */
    us1005_easy_provision("RQ11-01", US1005_SERVER_IP, 0, 0);

    /* If server-side parsing succeeded, the parsing error string should not be found */
    CU_ASSERT(search_target_found == 0);

    /* Restore CSR attributes to default for other tests */
    st_set_csrattrs(NULL);

    /* minimal frees consistent with exemplars */
    if (req) {
        X509_REQ_free(req);
    }
    if (key) {
        EVP_PKEY_free(key);
    }
}
